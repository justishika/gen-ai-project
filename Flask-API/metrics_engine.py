import json
import traceback

def calculate_coherence(answer, ollama_func):
    """
    Evaluates if the answer reads well and makes logical sense.
    Returns a score from 0.0 to 1.0.
    """
    prompt = f"""Rate the coherence of the following text on a scale from 1 to 5.
1 = Incoherent, confusing, or nonsensical.
5 = Perfectly clear, logical, and easy to understand.

Text:
"{answer}"

Respond ONLY with the number (1, 2, 3, 4, or 5)."""

    try:
        response = ollama_func(prompt)
        score = int(response.strip().split()[0]) # distinct text might be present
        return score / 5.0
    except Exception as e:
        print(f"Error calculating coherence: {e}")
        return 0.0

def calculate_correctness(answer, ground_truth, ollama_func):
    """
    Compares the AI answer against a Ground Truth reference.
    Returns a score from 0.0 to 1.0.
    """
    if not ground_truth:
        return None

    prompt = f"""Compare the AI Answer to the Ground Truth. 
Rate accuracy on a scale from 1 to 5.
1 = Completely wrong.
5 = Captures the meaning of the Ground Truth perfectly.

Ground Truth: "{ground_truth}"
AI Answer: "{answer}"

Respond ONLY with the number (1-5)."""

    try:
        response = ollama_func(prompt)
        score = int(response.strip().split()[0])
        return score / 5.0
    except Exception as e:
        print(f"Error calculating correctness: {e}")
        return 0.0

def evaluate_retrieval(question, contexts, ollama_func):
    """
    Evaluates retrieval quality: Context Precision, MRR, etc.
    'contexts' is a list of context strings or dictionaries.
    """
    if not contexts:
        return {
            "context_precision": 0.0,
            "mrr": 0.0,
            "context_recall_proxy": 0.0
        }

    # Prepare context list for LLM
    context_text = ""
    for i, c in enumerate(contexts):
        text = c if isinstance(c, str) else c.get('text', '')
        context_text += f"Chunk {i+1}: {text}\n\n"

    prompt = f"""Analyze the retrieved chunks for the question: "{question}"
    
For each Chunk (1 to {len(contexts)}), determine if it contains relevant information to answer the question.
Also determining if ALL chunks together provide SUFFICIENT info to answer the question.

Respond as a JSON object with this EXACT structure:
{{
  "relevant_chunks": [1, 3],  // List of indices (1-based) that are relevant
  "sufficient": true         // true/false
}}

Chunks:
{context_text}
"""

    try:
        response = ollama_func(prompt, format="json")
        if isinstance(response, str):
             response_json = json.loads(response)
        else:
             response_json = response

        relevant_indices = response_json.get("relevant_chunks", [])
        is_sufficient = response_json.get("sufficient", False)
        
        # 1. Context Precision = Relevant Chunks / Total Retrieved Chunks
        precision = len(relevant_indices) / len(contexts) if contexts else 0.0
        
        # 2. MRR (Mean Reciprocal Rank) = 1 / Rank of first relevant chunk
        mrr = 0.0
        if relevant_indices:
            first_relevant_rank = min(relevant_indices) # 1-based index
            mrr = 1.0 / first_relevant_rank

        # 3. Context Recall (Proxy)
        recall_score = 1.0 if is_sufficient else 0.5 # 0.5 if some relevance but not sufficient, 0 if no relevance? 
        # For simplicity, if sufficient=1.0, data present.

        return {
            "context_precision": precision,
            "mrr": mrr,
            "context_recall_proxy": recall_score
        }

    except Exception as e:
        print(f"Error calculating retrieval metrics: {e}")
        traceback.print_exc()
        return {
            "context_precision": 0.0,
            "mrr": 0.0,
            "context_recall_proxy": 0.0
        }
