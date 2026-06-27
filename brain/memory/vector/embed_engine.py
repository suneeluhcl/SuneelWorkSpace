#!/usr/bin/env python3
import os
import sys

# Redirect HF Hub cache to a local directory to bypass permission issues on global cache
os.environ["HF_HOME"] = "/Users/MAC/SuneelWorkSpace/brain/memory/vector/.hf_cache"

import argparse
import datetime
import logging
from sentence_transformers import SentenceTransformer
import chromadb

# Ensure log directory exists
log_dir = "/Users/MAC/SuneelWorkSpace/brain/memory/logs"
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=os.path.join(log_dir, "vector_embed.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

CHROMA_DIR = "/Users/MAC/SuneelWorkSpace/brain/memory/vector/chroma_store"
COLLECTION_NAME = "workspace_memory"

def get_content_type(file_path):
    lower_path = file_path.lower()
    if "decision" in lower_path:
        return "decision"
    elif "pattern" in lower_path:
        return "pattern"
    elif "insight" in lower_path:
        return "insight"
    elif "memory" in lower_path:
        return "memory"
    else:
        return "generic"

def chunk_text(text, chunk_size=350, overlap=50):
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        if i + chunk_size >= len(words):
            break
        i += (chunk_size - overlap)
    return chunks

def embed_and_store(content, source_file, content_type=None):
    if not content_type:
        content_type = get_content_type(source_file)
        
    logging.info(f"Starting embedding for {source_file} (type: {content_type})")
    
    # 1. Initialize sentence-transformers
    # The model 'all-MiniLM-L6-v2' will be downloaded/cached locally if not already present
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # 2. Chunk the text
    chunks = chunk_text(content)
    if not chunks:
        logging.warning(f"No text to embed in {source_file}")
        return
        
    logging.info(f"Split {source_file} into {len(chunks)} chunks")
    
    # 3. Initialize ChromaDB client
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 4. Idempotency: delete old entries for this source file
    collection.delete(where={"source_file": source_file})
    
    # 5. Embed and add
    ids = []
    documents = []
    metadatas = []
    
    embeddings = model.encode(chunks).tolist()
    
    timestamp = datetime.datetime.now().isoformat()
    
    for idx, chunk in enumerate(chunks):
        chunk_id = f"{source_file}_chunk_{idx}"
        ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({
            "source_file": source_file,
            "chunk_index": idx,
            "timestamp": timestamp,
            "content_type": content_type
        })
        
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    
    logging.info(f"Successfully embedded and stored {len(chunks)} chunks for {source_file}")
    print(f"Indexed {source_file}: {len(chunks)} chunks stored.")

def main():
    parser = argparse.ArgumentParser(description="Embed memory files into ChromaDB vector store")
    parser.add_argument("--file", help="Path to file to embed")
    parser.add_argument("--text", help="Raw text to embed")
    parser.add_argument("--source", help="Source identifier if text is provided")
    parser.add_argument("--type", help="Explicit content type override")
    
    args = parser.parse_args()
    
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: file {args.file} does not exist.")
            sys.exit(1)
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
        embed_and_store(content, args.file, args.type)
    elif args.text:
        source = args.source if args.source else "raw_text_input"
        embed_and_store(args.text, source, args.type)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
