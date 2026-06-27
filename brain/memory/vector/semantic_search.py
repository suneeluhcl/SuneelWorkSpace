#!/usr/bin/env python3
import os
import sys

# Redirect HF Hub cache to a local directory to bypass permission issues on global cache
os.environ["HF_HOME"] = "/Users/MAC/SuneelWorkSpace/brain/memory/vector/.hf_cache"

import argparse
import json
from sentence_transformers import SentenceTransformer
import chromadb

CHROMA_DIR = "/Users/MAC/SuneelWorkSpace/brain/memory/vector/chroma_store"
COLLECTION_NAME = "workspace_memory"

def query_vector_store(query_str, top_k=5, content_type=None, min_threshold=0.2):
    if not os.path.exists(CHROMA_DIR):
        # Store hasn't been created yet
        return []
        
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        # Collection doesn't exist yet
        return []
        
    # Get embeddings for query
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_vector = model.encode(query_str).tolist()
    
    # Query Chroma
    where_filter = {}
    if content_type:
        where_filter["content_type"] = content_type
        
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k * 2,  # Query more to allow filtering by threshold
        where=where_filter if where_filter else None
    )
    
    formatted_results = []
    if not results or not results["ids"] or not results["ids"][0]:
        return []
        
    ids = results["ids"][0]
    distances = results["distances"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    
    for i in range(len(ids)):
        # Since space is cosine, distance is 1 - cosine_similarity.
        # Cosine similarity = 1 - distance.
        distance = distances[i]
        similarity = 1.0 - distance
        
        if similarity < min_threshold:
            continue
            
        metadata = metadatas[i]
        formatted_results.append({
            "source": metadata.get("source_file", "unknown"),
            "score": round(similarity, 4),
            "excerpt": documents[i],
            "timestamp": metadata.get("timestamp", "")
        })
        
    # Sort by score descending and limit to top_k
    formatted_results = sorted(formatted_results, key=lambda x: x["score"], reverse=True)[:top_k]
    return formatted_results

def main():
    parser = argparse.ArgumentParser(description="Query the workspace vector memory")
    parser.add_argument("query", help="Natural language query string")
    parser.add_argument("-k", "--top-k", type=int, default=5, help="Number of results to return")
    parser.add_argument("-t", "--type", help="Filter by content type (memory/decision/insight/pattern)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--threshold", type=float, default=0.2, help="Similarity threshold (default 0.2)")
    
    args = parser.parse_args()
    
    results = query_vector_store(
        args.query,
        top_k=args.top_k,
        content_type=args.type,
        min_threshold=args.threshold
    )
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No matching memory entries found.")
            return
        print(f"\nSemantic Search Results for: '{args.query}' (Threshold: {args.threshold})")
        print("=" * 80)
        for idx, res in enumerate(results, 1):
            print(f"[{idx}] Source: {res['source']} (Score: {res['score']})")
            print(f"    Timestamp: {res['timestamp']}")
            print(f"    Excerpt: {res['excerpt']}")
            print("-" * 80)

if __name__ == "__main__":
    main()
