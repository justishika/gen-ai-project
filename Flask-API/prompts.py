# Prompt Templates for the GenAI Project

def get_summary_short_prompt(transcript_text):
    return f"""Task: Generate a summary of the provided video transcript in EXACTLY 10 numbered points.

Instructions:
1. Format as a strict numbered list (1., 2., 3., ...).
2. Each point must be concise but comprehensive.
3. STRICTLY use only the information from the transcript. Do not add outside knowledge or hallucinate.
4. Focus on the most important takeaways.

Transcript:
{transcript_text}
"""

def get_summary_detailed_prompt(transcript_text):
    return f"""Task: Provide a detailed, comprehensive summary of the video transcript in a structured, professional format (similar to IEEE/technical report style).

Instructions:
1. Use Numbered Headings for main sections (e.g., "1. Introduction", "2. Key Concept", "3. Conclusion").
2. Use Bullet Points under each heading to detail specific facts, arguments, and examples.
3. Be thorough: capture all technical details and nuances.
4. STRICTLY use only the information from the transcript. Do not hallucinate.

Transcript:
{transcript_text}
"""

def get_qa_prompt(context_text, question):
    return f"""You are a helpful assistant answering questions about a video based on its transcript.

CONTEXT:
{context_text}

QUESTION:
{question}

INSTRUCTIONS:
- Answer the question using ONLY the provided context.
- If the answer is not in the context, say "I don't have enough information in this part of the video to answer that."
- Be concise and helpful.
- Use natural language, not bullet points unless listing items.
"""

def get_entity_extraction_prompt(transcript_text):
    return f"""Analyze the following video transcript and extract key named entities and facts.
Return the result as a JSON object with the following keys:
- "key_facts": {{ "people_mentioned": int, "organizations": int, "locations": int, "dates_mentioned": int, "smart_insights": [str], "top_people": [{{ "name": str, "mentions": int }}], "top_organizations": [{{ "name": str, "mentions": int }}], "top_locations": [{{ "name": str, "mentions": int }}] }}
- "entities": {{ "PERSON": [{{ "text": str }}], "ORG": [{{ "text": str }}], "LOC": [{{ "text": str }}], "DATE": [{{ "text": str }}], "EVENT": [{{ "text": str }}] }}
- "timeline": [{{ "date": str, "context": str }}]
- "relationships": [{{ "type": str, "entity1": str, "entity2": str, "context": str }}]

Instructions for "smart_insights":
- Provide 5 distinct, interesting, and specific facts or "Did you know?" style takeaways from the video. 
- Do NOT just list what the video is about. Extract specific trivia or surprising details.


Respond ONLY with a single JSON object, no extra text.

Transcript:
{transcript_text}
"""

def get_insights_prompt(transcript_text):
    return f"""Generate 5 interesting questions that a user might want to ask about this video, and 3 key insights.
Format the output as a simple HTML string with:
<h3>Suggested Questions</h3><ul>...</ul>
<h3>Key Insights</h3><ul>...</ul>

Use only information from this transcript:

{transcript_text}
"""
