from flask import Flask, jsonify, request
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
import traceback
import json
import time

# Try to import config, but handle failure for Vercel deployment
try:
    from config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure Gemini
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in config.py or environment variables.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Use the model the user has quota for
GENERATION_MODEL = 'gemini-2.0-flash' 

# In-memory cache
# { video_id: { 'transcript': [...], 'vectorizer': obj, 'matrix': obj, 'chunks': [...] } }
CACHE = {}

# --- HELPER FUNCTIONS ---

def get_transcript(video_id):
    """Fetches transcript from YouTube."""
    try:
        # Instantiate the API (required for this version)
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        try:
            # Try to find English transcript
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except:
            # Fallback to any English (generated or manual)
            try:
                 transcript = transcript_list.find_generated_transcript(['en'])
            except:
                 # Last resort: take the first available one
                 transcript = next(iter(transcript_list))
            
        # Fetch returns a list of objects, we need to convert to dicts
        fetched = transcript.fetch()
        return [{'text': t.text, 'start': t.start, 'duration': t.duration} for t in fetched]

    except Exception as e:
        print(f"Transcript Error: {e}")
        return None

def create_rag_index(video_id, transcript_data):
    """
    Creates a simple TF-IDF index for the video.
    Splits transcript into chunks of ~1000 characters.
    """
    chunks = []
    current_chunk = ""
    current_start = 0
    
    for entry in transcript_data:
        text = entry['text']
        start = entry['start']
        
        if not current_chunk:
            current_start = start
            
        current_chunk += " " + text
        
        if len(current_chunk) > 1000:
            chunks.append({
                'text': current_chunk.strip(),
                'start': current_start
            })
            current_chunk = ""
            
    if current_chunk:
        chunks.append({'text': current_chunk.strip(), 'start': current_start})
        
    # Create TF-IDF Matrix
    texts = [c['text'] for c in chunks]
    vectorizer = TfidfVectorizer(stop_words='english')
    matrix = vectorizer.fit_transform(texts)
    
    return {
        'chunks': chunks,
        'vectorizer': vectorizer,
        'matrix': matrix
    }

def retrieve_context(video_id, query, top_k=5):
    """Retrieves relevant chunks using TF-IDF cosine similarity."""
    if video_id not in CACHE:
        return [], 0.0
        
    data = CACHE[video_id]
    vectorizer = data['vectorizer']
    matrix = data['matrix']
    chunks = data['chunks']
    
    # Vectorize query
    query_vec = vectorizer.transform([query])
    
    # Calculate similarity
    similarities = cosine_similarity(query_vec, matrix).flatten()
    
    # Get top K indices
    top_indices = similarities.argsort()[-top_k:][::-1]
    
    results = []
    top_score = 0.0
    
    if len(top_indices) > 0:
        top_score = float(similarities[top_indices[0]])
    
    for idx in top_indices:
        if similarities[idx] > 0.1: # Threshold
            results.append(chunks[idx])
            
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

# --- ROUTES ---

@app.route('/api/summary', methods=['GET'])
def summary():
    video_id = request.args.get('v')
    summary_type = request.args.get('type', 'short')
    
    if not video_id:
        return jsonify({"error": True, "data": "Video ID missing"})
        
    try:
        # 1. Get Transcript
        if video_id not in CACHE:
            transcript = get_transcript(video_id)
            if not transcript:
                return jsonify({"error": True, "data": "Could not retrieve transcript (no English captions?)"})
            
            # Build Index immediately for future Q&A
            index_data = create_rag_index(video_id, transcript)
            CACHE[video_id] = index_data
            
        # 2. Generate Summary
        chunks = CACHE[video_id]['chunks']
        full_text = " ".join([c['text'] for c in chunks])
        
        # Truncate if too long for context window (approx check)
        if len(full_text) > 50000:
            full_text = full_text[:50000] + "...(truncated)"
            
        # Construct Prompt based on type
        if summary_type == 'short':
            prompt = f"""Task: Generate a summary of the provided video transcript in EXACTLY 10 numbered points.
            
            Instructions:
            1. Format as a strict numbered list (1., 2., 3., ...).
            2. Each point must be concise but comprehensive.
            3. STRICTLY use only the information from the transcript. Do not add outside knowledge or hallucinate.
            4. Focus on the most important takeaways.
            
            Transcript:
            {full_text}"""
            
        elif summary_type == 'detailed':
            prompt = f"""Task: Provide a detailed, comprehensive summary of the video transcript in a structured, professional format (similar to IEEE/technical report style).
            
            Instructions:
            1. Use Numbered Headings for main sections (e.g., "1. Introduction", "2. Key Concept", "3. Conclusion").
            2. Use Bullet Points under each heading to detail specific facts, arguments, and examples.
            3. Be thorough: capture all technical details and nuances.
            4. STRICTLY use only the information from the transcript. Do not hallucinate.
            
            Transcript:
            {full_text}"""
        else:
            prompt = f"Summarize this video transcript:\n\n{full_text}"
        
        model = genai.GenerativeModel(GENERATION_MODEL)
        response = model.generate_content(prompt)
        
        return jsonify({"error": False, "data": response.text})
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": True, "data": str(e)})

@app.route('/api/ask', methods=['POST'])
def ask():
    start_time = time.time()
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        question = data.get('question')
        
        if not video_id or not question:
            return jsonify({"error": True, "data": "Missing video_id or question"})
            
        # 1. Ensure Index Exists
        if video_id not in CACHE:
            transcript = get_transcript(video_id)
            if not transcript:
                return jsonify({"error": True, "data": "Transcript not found. Please summarize first."})
            CACHE[video_id] = create_rag_index(video_id, transcript)
            
        # 2. Retrieve Context
        context_chunks, top_score = retrieve_context(video_id, question)
        
        if not context_chunks:
            return jsonify({"error": False, "data": "I couldn't find any relevant info in the video."})
            
        # 3. Generate Answer
        context_text = "\n\n".join([f"[Time: {int(c['start'])}s] {c['text']}" for c in context_chunks])
        
        prompt = f"""You are a helpful assistant answering questions about a video based on its transcript.
        
        CONTEXT:
        {context_text}
        
        QUESTION:
        {question}
        
        INSTRUCTIONS:
        - Answer the question using ONLY the provided context.
        - If the answer is not in the context, say "I don't know based on the video."
        - Be concise and helpful.
        """
        
        model = genai.GenerativeModel(GENERATION_MODEL)
        response = model.generate_content(prompt)
        answer = response.text
        
        # 4. Calculate Metrics
        latency = round(time.time() - start_time, 2)
        faithfulness = calculate_faithfulness(answer, context_text)
        
        return jsonify({
            "error": False, 
            "data": answer,
            "metrics": {
                "retrieval_score": float(top_score),
                "faithfulness": float(faithfulness),
                "latency": latency
            }
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
        # 1. Get Transcript
        if video_id not in CACHE:
            transcript = get_transcript(video_id)
            if not transcript:
                return jsonify({"error": True, "data": "Transcript not found."})
            CACHE[video_id] = create_rag_index(video_id, transcript)
            
        chunks = CACHE[video_id]['chunks']
        full_text = " ".join([c['text'] for c in chunks])
        if len(full_text) > 50000: full_text = full_text[:50000]
        
        # UPDATED PROMPT: Request objects with 'text' key to match frontend expectation
        prompt = f"""Analyze the following video transcript and extract key named entities and facts.
        Return the result as a JSON object with the following keys:
        - "key_facts": {{ "people_mentioned": int, "organizations": int, "locations": int, "dates_mentioned": int, "top_people": [{{ "name": str, "mentions": int }}], "top_organizations": [{{ "name": str, "mentions": int }}], "top_locations": [{{ "name": str, "mentions": int }}] }}
        - "entities": {{ "PERSON": [{{ "text": str }}], "ORG": [{{ "text": str }}], "LOC": [{{ "text": str }}], "DATE": [{{ "text": str }}], "EVENT": [{{ "text": str }}] }}
        - "timeline": [{{ "date": str, "context": str }}]
        - "relationships": [{{ "type": str, "entity1": str, "entity2": str, "context": str }}]
        
        Transcript:
        {full_text}
        """
        
        model = genai.GenerativeModel(GENERATION_MODEL, generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        
        # Parse JSON string to object to ensure valid JSON response
        try:
            data = json.loads(response.text)
            # Add success flag for frontend compatibility
            data['success'] = True
            return jsonify({"error": False, "data": data})
        except:
            return jsonify({"error": False, "data": response.text})
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": True, "data": str(e)})

@app.route('/api/get-insights', methods=['GET'])
def get_insights():
    video_id = request.args.get('v')
    if not video_id:
        return jsonify({"error": True, "data": "Video ID missing"})
        
    try:
        if video_id not in CACHE:
            transcript = get_transcript(video_id)
            if not transcript:
                return jsonify({"error": True, "data": "Transcript not found."})
            CACHE[video_id] = create_rag_index(video_id, transcript)
            
        chunks = CACHE[video_id]['chunks']
        full_text = " ".join([c['text'] for c in chunks])
        if len(full_text) > 50000: full_text = full_text[:50000]
        
        prompt = f"""Generate 5 interesting questions that a user might want to ask about this video, and 3 key insights.
        Format the output as a simple HTML string with <h3>Suggested Questions</h3><ul>...</ul> and <h3>Key Insights</h3><ul>...</ul>.
        
        Transcript:
        {full_text}
        """
        
        model = genai.GenerativeModel(GENERATION_MODEL)
        response = model.generate_content(prompt)
        
        return jsonify({"error": False, "data": response.text})
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": True, "data": str(e)})

# --- STARTUP ---
if __name__ == '__main__':
    print("!!! FRESH START SERVER V3.8 (VERCEL READY) !!!")
    print(f"Using Model: {GENERATION_MODEL}")
    app.run(port=5000, debug=False)