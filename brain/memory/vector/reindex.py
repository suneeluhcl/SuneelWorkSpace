#!/usr/bin/env python3
import os
import sys
import glob
import logging

# Ensure we can import embed_engine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from embed_engine import embed_and_store, CHROMA_DIR, COLLECTION_NAME
import chromadb

# Configure logging
log_dir = "/Users/MAC/SuneelWorkSpace/brain/memory/logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "vector_embed.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def clear_collection():
    logging.info("Clearing ChromaDB collection for clean re-indexing")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(name=COLLECTION_NAME)
        logging.info("Deleted existing collection")
    except Exception:
        logging.info("Collection did not exist prior to clear")

def main():
    print("Starting full vector memory re-indexing...")
    clear_collection()
    
    # Files to index from Step 1.5
    files_to_index = [
        "brain/memory/MEMORY.md",
        "brain/memory/DECISIONS.md",
        "brain/memory/PATTERNS.md",
        "brain/memory/INSIGHTS.md",
        "brain/memory/SESSION_HANDOFF.md",
        "dna/identity/profile/identity_profile.md",
        "dna/identity/profile/decision_profile.md"
    ]
    
    # Find all files in brain/research/decisions/
    research_decisions = glob.glob("brain/research/decisions/**/*.md", recursive=True)
    files_to_index.extend(research_decisions)
    
    # Find all files in brain/decisions/ (if it exists)
    brain_decisions = glob.glob("brain/decisions/**/*.md", recursive=True)
    files_to_index.extend(brain_decisions)
    
    indexed_count = 0
    for file_path in files_to_index:
        full_path = os.path.join("/Users/MAC/SuneelWorkSpace", file_path)
        # Normalize and remove double slashes
        full_path = os.path.abspath(full_path)
        
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Store with path relative to SuneelWorkSpace for consistency
                rel_path = os.path.relpath(full_path, "/Users/MAC/SuneelWorkSpace")
                embed_and_store(content, rel_path)
                indexed_count += 1
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")
                logging.error(f"Error indexing {file_path}: {e}")
        else:
            # File might not exist (e.g. optional directories like brain/decisions)
            logging.info(f"Skipping {file_path} (does not exist or is not a file)")
            
    print(f"Full re-indexing completed. Successfully indexed {indexed_count} files.")

if __name__ == "__main__":
    main()
