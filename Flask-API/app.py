from flask import Flask, jsonify, request
import re
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
import traceback
import json
import time
import requests
import sys


# Try to import config, but handle failure for Vercel deployment
try:
    from config import OLLAMA_API_KEY, OLLAMA_MODEL, OLLAMA_BASE_URL, CHUNK_SIZE
except ImportError:
    OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")
    # default model if not provided via env/config
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:20b")
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com/api")
    CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 500))

# --- CONFIGURATION ---
import logging

# Setup logging
logging.basicConfig(
    filename='backend.log',
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)

app = Flask(__name__)
print("!!! APP.PY LOADED WITH DEBUG PRINTS !!!", flush=True)
app.secret_key = os.urandom(24)

CORS(app, resources={r"/*": {"origins": "*"}})

# OLLAMA_BASE_URL is now from config or env

if not OLLAMA_API_KEY:
    print("WARNING: OLLAMA_API_KEY not found in config.py or environment variables.")
    logging.warning("OLLAMA_API_KEY not found.")
else:
    print("Ollama Cloud configured. Model:", OLLAMA_MODEL)


# In-memory cache
# { video_id: { 'transcript': [...], 'vectorizer': obj, 'matrix': obj, 'chunks': [...] } }
CACHE = {}


# --- HELPER: OLLAMA CLOUD CALLS ---

def ollama_generate(prompt, *, model=None, format=None):
    """
    Call Ollama Cloud /api/generate.
    - prompt: string
    - model: optional model name, default OLLAMA_MODEL
    - format: None, "json", or JSON schema (dict)
    Returns:
        data["response"] (can be str or dict depending on 'format').
    """
    if not OLLAMA_API_KEY:
        raise RuntimeError("OLLAMA_API_KEY is not configured.")

    if model is None:
        model = OLLAMA_MODEL

    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    if format is not None:
        payload["format"] = format

    resp = requests.post(
        f"{OLLAMA_BASE_URL}/generate",
        headers=headers,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    # For normal text, this is a string.
    # For JSON mode/structured outputs, this can be a dict.
    return data.get("response")


# --- HELPER FUNCTIONS ---
def get_transcript(video_id):
    """Fetches transcript from YouTube with robust fallback."""
    try:
        # Get list of available transcripts
        # NOTE: Installed version requires instantiation and uses .list()
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # Priority list of languages to try
        # 1. Manually created English
        # 2. Auto-generated English
        # 3. Any other available transcript
        
        candidates = []
        
        # Collect candidates
        try:
            candidates.append(transcript_list.find_transcript(['en']))
        except:
            pass
            
        try:
            candidates.append(transcript_list.find_generated_transcript(['en']))
        except:
            pass
            
        # Add all others as backup
        for t in transcript_list:
            if t not in candidates:
                candidates.append(t)
                
        if not candidates:
            print("No transcripts available found in list.")
            return None

        # Try fetching from candidates in order
        transcript_data = None
        for transcript in candidates:
            try:
                print(f"Attempting to fetch transcript: {transcript.language_code} ({'Generated' if transcript.is_generated else 'Manual'})")
                transcript_data = transcript.fetch()
                if transcript_data:
                    break
            except Exception as e:
                print(f"Failed to fetch transcript {transcript.language_code}: {e}")
                continue
        
        if not transcript_data:
            print("All transcript fetch attempts failed.")
            return None
        
        # Convert to our format
        return [
            {
                'text': entry.text if hasattr(entry, 'text') else entry['text'],
                'start': entry.start if hasattr(entry, 'start') else entry['start'],
                'duration': entry.duration if hasattr(entry, 'duration') else entry['duration']
            }
            for entry in transcript_data
        ]

    except Exception as e:
        print(f"Transcript Error (Top Level): {e}")
        traceback.print_exc()
        return None
         


# --- RAG INTEGRATION (NEW) ---
import rag_engine
import metrics_engine
import prompts
import threading

# Lock for ChromaDB writes
rag_lock = threading.Lock()

def create_rag_index(video_id, transcript_data):
    """
    Indexes the video transcript using ChromaDB (handled by rag_engine).
    Protected by lock to prevent concurrent writes.
    """
    with rag_lock:
        chunks = []
        current_chunk = ""
        current_start = 0

        for entry in transcript_data:
            text = entry['text']
            start = entry['start']

            if not current_chunk:
                current_start = start

            current_chunk += " " + text

            # Keep chunk size reasonable for embedding models
            if len(current_chunk) > CHUNK_SIZE:
                chunks.append({
                    'text': current_chunk.strip(),
                    'start': current_start
                })
                current_chunk = ""
                current_start = start # Update start for next chunk

        if current_chunk:
            chunks.append({'text': current_chunk.strip(), 'start': current_start})
        
        # Store in ChromaDB
        rag_engine.add_video_to_index(video_id, chunks)

        # Return chunks for basic usage if needed, but Vector DB is primary now
        return {'chunks': chunks}

def retrieve_context(video_id, query, top_k=5):
    """Retrieves relevant chunks using ChromaDB Semantic Search."""
    results = rag_engine.query_index(video_id, query, k=top_k)
    
    # Calculate a "match score" based on distance
    # chroma returns L2 distance by default (lower is better) or cosine distance
    # We'll just return the raw results and handle scoring loosely
    
    top_score = 0.0
    if results:
        # Inverse distance as score roughly? 
        # For L2, 0 is perfect. For Cosine Distance, 0 is perfect (1 - similarity).
        # SentencesTransformers defaults to Cosine Similarity usually, but Chroma default is L2.
        # Let's just return the first result's "distance" as is, or invert it for UI.
        # Here we just pass it through.
        top_score = 1.0 - results[0]['distance'] # Approximate similarity
    
    return results, top_score

def calculate_faithfulness(answer, context_text):
    """
    Calculates a simple faithfulness score based on word overlap (ROUGE-1 like).
    """
    answer_words = set(answer.lower().split())
    context_words = set(context_text.lower().split())

    if not answer_words:
        return 0.0

    overlap = answer_words.intersection(context_words)
    return len(overlap) / len(answer_words)





# --- ASYNC PROCESSING (NEW) ---
import threading
import uuid

# In-memory Job Store (for demo purposes)
JOBS = {}

def async_summarize_task(job_id, video_id, summary_type):
    """Background task for summarization."""
    try:
        # NOTE: In a real app, we need app context here if interacting with Flask extensions.
        # But we are just calling our helper functions which use libraries directly or global config.
        # However, app.py functions rely on 'OLLAMA_API_KEY' global. That's fine.
        
        JOBS[job_id]['status'] = 'processing'
        
        # Reuse existing logic
        if not OLLAMA_API_KEY:
             raise ValueError("OLLAMA_API_KEY not configured.")

        # 1. Get Transcript
        transcript = get_transcript(video_id)
        if not transcript:
            raise ValueError("Could not retrieve transcript.")

        # Indexing
        create_rag_index(video_id, transcript) 

        # 2. Summary Prompt
        chunks = [
            {'text': entry.text if hasattr(entry, 'text') else entry['text']} 
            for entry in transcript
        ]
        full_text = " ".join([c['text'] for c in chunks])
        if len(full_text) > 50000:
             full_text = full_text[:50000] + "..."

        if summary_type == 'short':
             prompt = prompts.get_summary_short_prompt(full_text)
        else:
             prompt = prompts.get_summary_detailed_prompt(full_text)

        response_text = ollama_generate(prompt)
        
        JOBS[job_id]['status'] = 'completed'
        JOBS[job_id]['result'] = response_text
        
    except Exception as e:
        JOBS[job_id]['status'] = 'failed'
        JOBS[job_id]['error'] = str(e)
        traceback.print_exc()

@app.route('/api/submit-summary', methods=['POST'])
def submit_summary():
    video_id = request.json.get('video_id')
    summary_type = request.json.get('type', 'short')
    
    if not video_id:
        return jsonify({"error": True, "data": "Video ID missing"})

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {'status': 'queued'}
    
    # Run in background thread
    thread = threading.Thread(target=async_summarize_task, args=(job_id, video_id, summary_type))
    thread.daemon = True # Kill thread if main process dies
    thread.start()
    
    return jsonify({"error": False, "job_id": job_id, "status": "queued"})


@app.route('/api/check-status/<job_id>', methods=['GET'])
def check_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": True, "data": "Job not found"})
        
    return jsonify({
        "error": False, 
        "status": job['status'], 
        "result": job.get('result'),
        "error_msg": job.get('error')
    })




# --- ROUTES ---

@app.route('/api/summary', methods=['GET'])
def summary():
    video_id = request.args.get('v')
    summary_type = request.args.get('type', 'short')

    if not video_id:
        return jsonify({"error": True, "data": "Video ID missing"})

    try:
        if not OLLAMA_API_KEY:
            return jsonify({"error": True, "data": "Server LLM not configured (OLLAMA_API_KEY missing)."})
            
        print(f"DEBUG: Summary requested for {video_id}. CACHE keys: {list(CACHE.keys())}")

        # 1. Get Transcript
        if video_id not in CACHE:
            print(f"DEBUG: {video_id} not in CACHE. Fetching...")
            transcript = get_transcript(video_id)
            if not transcript:
                print("DEBUG: Failed to fetch transcript.")
                return jsonify({"error": True, "data": "Could not retrieve transcript (no English captions?)"})

            # Build Index immediately for future Q&A
            print("DEBUG: Creating RAG index...")
            index_data = create_rag_index(video_id, transcript)
            CACHE[video_id] = index_data
            print(f"DEBUG: Added {video_id} to CACHE.")
        else:
            print(f"DEBUG: {video_id} found in CACHE.")

        # 2. Generate Summary
        chunks = CACHE[video_id]['chunks']
        full_text = " ".join([c['text'] for c in chunks])

        # Truncate if too long
        if len(full_text) > 50000:
            full_text = full_text[:50000] + "...(truncated)"

        if summary_type == 'short':
            prompt = prompts.get_summary_short_prompt(full_text)
        elif summary_type == 'detailed':
            prompt = prompts.get_summary_detailed_prompt(full_text)
        else:
            prompt = prompts.get_summary_short_prompt(full_text) # Default fallback

        response_text = ollama_generate(prompt)
        return jsonify({"error": False, "data": response_text})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": True, "data": str(e)})


@app.route('/api/ask', methods=['POST'])
def ask():
    start_time = time.time()
    print("DEBUG: Executing Ask V2 (Metrics Update)")

    try:
        data = request.get_json()
        video_id = data.get('video_id')
        video_id = data.get('video_id')
        question = data.get('question')
        ground_truth = data.get('ground_truth')

        if not video_id or not question:
            return jsonify({"error": True, "data": "Missing video_id or question"})

        if not OLLAMA_API_KEY:
            return jsonify({"error": True, "data": "Server LLM not configured (OLLAMA_API_KEY missing)."})

        print(f"DEBUG: Ask requested for {video_id}. CACHE keys: {list(CACHE.keys())}")

        # 1. Ensure Index Exists
        # Check if we have it in memory or if it needs to be loaded/indexed
        if video_id not in CACHE:
             print(f"DEBUG: {video_id} NOT in CACHE during Ask. Attempting fetch...")
             # Try to see if it's already in ChromaDB? 
             # For simplicity, we just check if we have the transcript. 
             # If not, we fetch transcript + index.
             # Ideally we check rag_engine.collection_exists(video_id) but let's stick to flow:
             
             transcript = get_transcript(video_id)
             if not transcript:
                 print("DEBUG: Transcript fetch failed during Ask.")
                 # If we can't get transcript, we can't answer (unless already indexed, but let's assume not)
                 return jsonify({"error": True, "data": "Transcript not found. Please summarize first."})
             
             CACHE[video_id] = create_rag_index(video_id, transcript)
             print(f"DEBUG: Added {video_id} to CACHE during Ask.")


        # Shortcuts for "hi" and "what is this video" have been removed to ensure metrics are always calculated.

        # 2. Retrieve Context
        context_chunks, top_score = retrieve_context(video_id, question, top_k=5)

        if not context_chunks:
            return jsonify({
                "error": False,
                "data": "I couldn't find specific information about that in the video. Could you rephrase your question or ask something more specific?"
            })

        # 3. Generate Answer
        context_text = "\n\n".join(
            [f"[Time: {int(c['start'])}s] {c['text']}" for c in context_chunks]
        )

        prompt = prompts.get_qa_prompt(context_text, question)

        answer = ollama_generate(prompt)

        latency = round(time.time() - start_time, 2)
        
        # --- Advanced Evaluation Metrics ---
        faithfulness = calculate_faithfulness(answer, context_text)
        
        # Answer Relevance
        answer_relevance = rag_engine.calculate_cosine_similarity(question, answer)
        
        # Coherence (LLM-based)
        coherence = metrics_engine.calculate_coherence(answer, ollama_generate)
        
        # Correctness (optional, requires ground_truth)
        correctness = metrics_engine.calculate_correctness(answer, ground_truth, ollama_generate)
        
        # Retrieval Metrics (LLM-based)
        retrieval_stats = metrics_engine.evaluate_retrieval(question, context_chunks, ollama_generate)
        
        metrics = {
                "retrieval_score": float(top_score), # Raw distance metric
                "faithfulness": float(faithfulness),
                "answer_relevance": float(answer_relevance),
                "coherence": float(coherence),
                "correctness": float(correctness) if correctness is not None else None,
                "context_precision": float(retrieval_stats["context_precision"]),
                "context_recall": float(retrieval_stats["context_recall_proxy"]),
                "mrr": float(retrieval_stats["mrr"]),
                "latency": latency
            }
        print(f"DEBUG: Returning Metrics: {metrics}")
        return jsonify({
            "error": False,
            "data": answer,
            "metrics": metrics
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": True, "data": f"Backend Error: {str(e)}"})


@app.route('/api/extract-entities', methods=['GET'])
def extract_entities():
    video_id = request.args.get('v')
    if not video_id:
        return jsonify({"error": True, "data": "Video ID missing"})

    try:
        if not OLLAMA_API_KEY:
            return jsonify({"error": True, "data": "Server LLM not configured (OLLAMA_API_KEY missing)."})

        # 1. Get Transcript
        if video_id not in CACHE:
            transcript = get_transcript(video_id)
            if not transcript:
                return jsonify({"error": True, "data": "Transcript not found."})
            CACHE[video_id] = create_rag_index(video_id, transcript)

        chunks = CACHE[video_id]['chunks']
        full_text = " ".join([c['text'] for c in chunks])
        if len(full_text) > 50000:
            full_text = full_text[:50000]

        # Ask Ollama to return JSON. We also set format="json".
        # Ask Ollama to return JSON. We also set format="json".
        prompt = prompts.get_entity_extraction_prompt(full_text)

        # JSON mode
        raw_response = ollama_generate(prompt, format="json")

        # Clean potential markdown code blocks (common with some models)
        if isinstance(raw_response, str):
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            raw_response = cleaned_response.strip()

        # raw_response may already be a dict (structured output) or a JSON string
        if isinstance(raw_response, dict):
            data = raw_response
        else:
            try:
                # 1. Try direct parse
                data = json.loads(raw_response)
            except Exception:
                # 2. Try regex extraction to find { ... }
                print(f"WARN: Direct JSON parse failed. Attempting regex extraction. Raw start: {raw_response[:100]}...")
                try:
                    # Look for the first outer brace to the last outer brace
                    match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                        data = json.loads(json_str)
                    else:
                        raise ValueError("No JSON-like object found in response string.")
                except Exception as e:
                    print(f"ERROR: JSON Extraction and Parse failed: {e}")
                    # fallback: wrap as text if not valid JSON so frontend displays it as text
                    return jsonify({"error": False, "data": {"error_text": raw_response}})

        data['success'] = True
        return jsonify({"error": False, "data": data})

    except Exception as e:
        traceback.print_exc()
        logging.error(f"Extract Entities Failed: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({"error": True, "data": str(e)})


@app.route('/api/get-insights', methods=['GET'])
def get_insights():
    video_id = request.args.get('v')
    if not video_id:
        return jsonify({"error": True, "data": "Video ID missing"})

    try:
        if not OLLAMA_API_KEY:
            return jsonify({"error": True, "data": "Server LLM not configured (OLLAMA_API_KEY missing)."})

        if video_id not in CACHE:
            transcript = get_transcript(video_id)
            if not transcript:
                return jsonify({"error": True, "data": "Transcript not found."})
            CACHE[video_id] = create_rag_index(video_id, transcript)

        chunks = CACHE[video_id]['chunks']
        full_text = " ".join([c['text'] for c in chunks])
        if len(full_text) > 50000:
            full_text = full_text[:50000]

        prompt = prompts.get_insights_prompt(full_text)

        html = ollama_generate(prompt)
        return jsonify({"error": False, "data": html})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": True, "data": str(e)})


# --- STARTUP ---
if __name__ == '__main__':
    print("!!! FRESH START SERVER (OLLAMA CLOUD) !!!")
    print(f"Using Ollama Model: {OLLAMA_MODEL}")
    app.run(port=5000, debug=False)



