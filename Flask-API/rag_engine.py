
import chromadb
from chromadb.utils import embedding_functions
import os
import uuid

import config

# Initialize Chroma Client (Persistent)
# Stores data in 'chroma_db' folder in current directory
CHROMA_DATA_PATH = config.CHROMA_DATA_PATH
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

# Use a standard, small, high-quality model
# all-MiniLM-L6-v2 is fast and good for general English
EMBEDDING_MODEL_NAME = config.EMBEDDING_MODEL_NAME
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL_NAME
)

def get_or_create_collection(video_id):
    """
    Creates or retrieves a collection for a specific video.
    We use one collection per video to keep searches scoped.
    Collection name must be valid, so we prefix and sanitize.
    """
    safe_name = f"video_{video_id}".replace("-", "_") # minimal sanitization
    return client.get_or_create_collection(
        name=safe_name,
        embedding_function=embedding_function
    )

def add_video_to_index(video_id, chunks):
    """
    Adds transcript chunks to the ChromaDB collection.
    """
    collection = get_or_create_collection(video_id)
    
    # Check if already populated to avoid duplicates/re-embedding cost
    if collection.count() > 0:
        print(f"Video {video_id} already indexed in ChromaDB.")
        return

    print(f"Indexing {len(chunks)} chunks for video {video_id}...")
    
    ids = [str(uuid.uuid4()) for _ in chunks]
    documents = [c['text'] for c in chunks]
    metadatas = [{'start': c['start']} for c in chunks]
    
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    print("Indexing complete.")

def query_index(video_id, query, k=5):
    """
    Queries the ChromaDB collection for the video.
    """
    try:
        collection = get_or_create_collection(video_id)
        
        results = collection.query(
            query_texts=[query],
            n_results=k
        )
        
        # Chroma returns list of lists (one per query)
        # Structure: {'documents': [[...]], 'metadatas': [[...]], 'distances': [[...]]}
        
        parsed_results = []
        if results['documents']:
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            distances = results['distances'][0] # distance (lower is better for L2, but we usually want similarity)
            
            for i in range(len(docs)):
                parsed_results.append({
                    'text': docs[i],
                    'start': metas[i]['start'],
                    'distance': distances[i]
                })
                
        return parsed_results
        
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")
        return []

def delete_index(video_id):
    """
    Deletes the collection (useful for cleanup or re-indexing).
    """
    safe_name = f"video_{video_id}".replace("-", "_")
    try:
        client.delete_collection(safe_name)
    except:
        pass

def calculate_cosine_similarity(text1, text2):
    """
    Calculates cosine similarity between two texts using the embedding model.
    """
    # Generate embeddings
    embeddings = embedding_function([text1, text2])
    emb1 = embeddings[0]
    emb2 = embeddings[1]
    
    # Calculate cosine similarity manually to avoid extra dependencies if possible
    # (dot product / (norm1 * norm2))
    dot_product = sum(a*b for a, b in zip(emb1, emb2))
    norm1 = sum(a*a for a in emb1) ** 0.5
    norm2 = sum(b*b for b in emb2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return dot_product / (norm1 * norm2)
