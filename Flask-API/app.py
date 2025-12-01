from flask import Flask, jsonify, request, session
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, InvalidVideoId
from config import GEMINI_API_KEY
from flask_cors import CORS
from ner_extractor import process_transcript
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
CORS(app, supports_credentials=True)

# Store transcripts temporarily (in production, use Redis or database)
transcript_cache = {}

@app.route('/summary', methods=['GET'])
def youtube_summarizer():
    video_id = request.args.get('v')
    summary_type = request.args.get('type', 'short')
    
    # Validate video_id
    if not video_id:
        return jsonify({"data": "Video ID is required", "error": True}), 400
    
    try:
        transcript = get_transcript(video_id)
        
        # Validate transcript is not empty
        if not transcript or len(transcript.strip()) == 0:
            return jsonify({"data": "No transcript content found for this video", "error": True}), 400
        
        # Cache the transcript for Q&A feature
        transcript_cache[video_id] = transcript
        
        summary = gemini_summarize(transcript, summary_type)
    except NoTranscriptFound:
        return jsonify({"data": "No English Subtitles found", "error": True})
    except InvalidVideoId:
        return jsonify({"data": "Invalid Video Id", "error": True})
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"Error in youtube_summarizer: {error_type}: {error_msg}")
        print(f"Full error details: {repr(e)}")
        
        # Provide more specific error messages - only check for actual API key errors
        # Be very specific to avoid false positives - only show API key error if it's explicitly about the API key
        is_api_key_error = (
            ("Gemini API key missing" in error_msg) or
            ("Invalid Gemini API key" in error_msg) or
            ("Failed to configure Gemini API" in error_msg) or
            ("API key missing" in error_msg and "GEMINI_API_KEY" in error_msg) or
            ("invalid API key" in error_msg.lower() and "gemini" in error_msg.lower())
        )
        
        if is_api_key_error:
            return jsonify({"data": "API key error. Please check your Gemini API key configuration.", "error": True})
        elif "transcript" in error_msg.lower() and ("not found" in error_msg.lower() or "no transcript" in error_msg.lower()):
            return jsonify({"data": "Error fetching transcript. The video may not have captions available.", "error": True})
        elif "InvalidVideoId" in error_type or "NoTranscriptFound" in error_type:
            # These are already handled above, but just in case
            return jsonify({"data": error_msg, "error": True})
        else:
            # For other errors, return the actual error message
            return jsonify({"data": error_msg if error_msg else "Unable to Summarize the video", "error": True})
    
    return jsonify({"data": summary, "error": False})

@app.route('/ask', methods=['POST'])
def ask_question():
    """Handle Q&A about the video"""
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        question = data.get('question')
        conversation_history = data.get('history', [])
        
        if not video_id or not question:
            return jsonify({"data": "Missing video_id or question", "error": True})
        
        # Get transcript from cache or fetch it
        if video_id not in transcript_cache:
            transcript = get_transcript(video_id)
            transcript_cache[video_id] = transcript
        else:
            transcript = transcript_cache[video_id]
        
        # Generate answer using Gemini
        answer = gemini_answer_question(transcript, question, conversation_history)
        
        return jsonify({"data": answer, "error": False})
    
    except Exception as e:
        print(f"Error in ask_question: {repr(e)}")
        return jsonify({"data": "Unable to answer the question", "error": True})

@app.route('/get-insights', methods=['GET'])
def get_insights():
    """Generate automatic insights about the video"""
    video_id = request.args.get('v')
    
    try:
        if video_id not in transcript_cache:
            transcript = get_transcript(video_id)
            transcript_cache[video_id] = transcript
        else:
            transcript = transcript_cache[video_id]
        
        insights = gemini_generate_insights(transcript)
        return jsonify({"data": insights, "error": False})
    
    except Exception as e:
        print(f"Error generating insights: {repr(e)}")
        return jsonify({"data": "Unable to generate insights", "error": True})

@app.route('/extract-entities', methods=['GET'])
def extract_entities_endpoint():
    """Extract named entities, timeline, facts, and relationships from video transcript"""
    video_id = request.args.get('v')
    
    if not video_id:
        return jsonify({"data": "Video ID is required", "error": True}), 400
    
    try:
        # Get transcript from cache or fetch it
        if video_id not in transcript_cache:
            transcript = get_transcript(video_id)
            transcript_cache[video_id] = transcript
        else:
            transcript = transcript_cache[video_id]
        
        # Process transcript with NER
        result = process_transcript(transcript)
        
        if not result.get('success'):
            return jsonify({"data": result.get('error', 'NER processing failed'), "error": True}), 500
        
        return jsonify({"data": result, "error": False})
    
    except NoTranscriptFound:
        return jsonify({"data": "No English Subtitles found", "error": True})
    except InvalidVideoId:
        return jsonify({"data": "Invalid Video Id", "error": True})
    except Exception as e:
        error_msg = str(e)
        print(f"Error in extract_entities_endpoint: {error_msg}")
        
        # Check if it's a model download error
        if "spaCy model not found" in error_msg or "download" in error_msg.lower():
            return jsonify({
                "data": "NER model not installed. Please run: python -m spacy download en_core_web_sm",
                "error": True
            }), 500
        
        return jsonify({"data": f"Unable to extract entities: {error_msg}", "error": True}), 500

def get_transcript(video_id):
    api = YouTubeTranscriptApi()
    transcript_response = None
    last_exc = None
    
    for method in ("get_transcript", "fetch", "list"):
        if hasattr(api, method):
            func = getattr(api, method)
            try:
                if method == "list":
                    resp = func(video_id)
                    if hasattr(resp, 'fetch'):
                        transcript_response = resp.fetch()
                    else:
                        transcript_response = resp
                else:
                    transcript_response = func(video_id)
                print(f"get_transcript: used method '{method}'")
                break
            except Exception as e:
                last_exc = e
                continue
    
    if transcript_response is None:
        raise last_exc or Exception("No transcript method succeeded")
    
    texts = []
    if hasattr(transcript_response, '__iter__') and not isinstance(transcript_response, (str, bytes, dict)):
        try:
            for item in transcript_response:
                if isinstance(item, dict):
                    t = item.get('text')
                    if t:
                        texts.append(t)
                elif hasattr(item, 'text'):
                    if item.text:
                        texts.append(item.text)
                elif isinstance(item, str):
                    texts.append(item)
            if texts:
                joined = ' '.join(texts)
                print(f"get_transcript: transcript length={len(joined)}")
                return joined
        except Exception as e:
            print(f"Failed to iterate response: {repr(e)}")
    
    if hasattr(transcript_response, 'entries'):
        for entry in transcript_response.entries:
            if isinstance(entry, dict):
                t = entry.get('text')
                if t:
                    texts.append(t)
            elif hasattr(entry, 'text'):
                if entry.text:
                    texts.append(entry.text)
    elif isinstance(transcript_response, list):
        for item in transcript_response:
            if isinstance(item, dict):
                t = item.get('text') or item.get('transcript')
                if t:
                    texts.append(t)
            elif isinstance(item, str):
                texts.append(item)
            elif hasattr(item, 'text'):
                if item.text:
                    texts.append(item.text)
    elif isinstance(transcript_response, dict):
        t = transcript_response.get('text') or transcript_response.get('transcript')
        if t:
            texts.append(t)
    elif isinstance(transcript_response, str):
        texts.append(transcript_response)
    else:
        raise Exception(f"Unknown transcript response type: {type(transcript_response)!r}")
    
    joined = ' '.join(texts)
    print(f"get_transcript: transcript length={len(joined)}")
    return joined

def gemini_summarize(transcript, summary_type='short'):
    api_key = os.environ.get('GEMINI_API_KEY') or GEMINI_API_KEY
    if not api_key or not api_key.strip() or api_key == 'YOUR_ACTUAL_API_KEY_HERE':
        raise Exception('Gemini API key missing; set GEMINI_API_KEY or update config.py')
    
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Error configuring Gemini API: {repr(e)}")
        raise Exception(f"Failed to configure Gemini API: {str(e)}")
    
    max_chars = 60000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n\n[Truncated transcript]"
    
    if summary_type == 'detailed':
        prompt = f"""You have to provide a detailed, in-depth summary of the following YouTube video transcript.
Break it down into key sections with clear headings and bullet points.
Capture all the important details, examples, and nuances.
Format your response with clear sections and use numbered lists or bullet points for better readability.

Transcript:
{transcript}"""
    else:
        prompt = f"""You have to summarize a YouTube video using its transcript in exactly 10 concise points.
Format each point clearly starting with a number (1., 2., 3., etc.).
Each point should be on a new line and be substantial enough to convey meaningful information.
Make sure the summary is comprehensive and covers the main topics discussed in the video.

Transcript:
{transcript}"""
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        print("Gemini request succeeded")
        return response.text
    except Exception as e:
        error_str = str(e)
        error_repr = repr(e)
        print(f"Gemini request failed: {error_repr}")
        
        # Check for specific Gemini API errors
        if "403" in error_str or "leaked" in error_str.lower() or "reported" in error_str.lower():
            raise Exception("Your API key has been flagged as leaked. Please generate a new API key from https://aistudio.google.com/app/apikey and update it in Flask-API/config.py")
        elif "API_KEY_INVALID" in error_str or "invalid API key" in error_str.lower() or "API key not valid" in error_str or "not valid" in error_str.lower():
            raise Exception("Invalid Gemini API key. Please check your API key in Flask-API/config.py. Make sure you've added a valid API key (not the placeholder 'YOUR_API_KEY_HERE')")
        elif "quota" in error_str.lower() or "rate limit" in error_str.lower():
            raise Exception("Gemini API quota exceeded or rate limit reached. Please try again later.")
        elif "safety" in error_str.lower() or "blocked" in error_str.lower():
            raise Exception("Content was blocked by Gemini safety filters. Try a different video.")
        else:
            # Re-raise with more context
            raise Exception(f"Gemini API error: {error_str}")

def gemini_answer_question(transcript, question, conversation_history=[]):
    """Answer questions about the video using Gemini"""
    api_key = os.environ.get('GEMINI_API_KEY') or GEMINI_API_KEY
    genai.configure(api_key=api_key)
    
    max_chars = 60000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n\n[Truncated transcript]"
    
    # Build conversation context
    context = "Previous conversation:\n"
    for msg in conversation_history[-4:]:  # Keep last 4 exchanges
        context += f"Q: {msg['question']}\nA: {msg['answer']}\n\n"
    
    prompt = f"""You are an AI assistant helping users understand a YouTube video. 
Based on the video transcript below, answer the user's question accurately and concisely.
If the question cannot be answered from the transcript, politely say so.

{context if conversation_history else ''}

Video Transcript:
{transcript}

User's Question: {question}

Answer the question in a clear, helpful manner. If relevant, mention specific details or timestamps from the video."""
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini Q&A failed:", repr(e))
        raise

def gemini_generate_insights(transcript):
    """Generate automatic insights about the video"""
    api_key = os.environ.get('GEMINI_API_KEY') or GEMINI_API_KEY
    genai.configure(api_key=api_key)
    
    max_chars = 60000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n\n[Truncated transcript]"
    
    prompt = f"""Analyze this YouTube video transcript and provide:
1. Main Topic (one sentence)
2. Key Takeaways (3-4 bullet points)
3. Target Audience
4. Content Type (Tutorial, Review, Educational, Entertainment, etc.)
5. Suggested Questions viewers might want to ask

Format your response clearly with these sections.

Transcript:
{transcript}"""
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini insights failed:", repr(e))
        raise

if __name__ == '__main__':
    app.run(debug=True, port=5000)