import os
import re
import csv
import json
import uuid
from datetime import datetime, timezone
import numpy as np
import chromadb

TIMESTAMP_NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def batch_upsert_to_chroma():
    project_root = "/Users/ada/myprojects/my-first-app"
    data_dir = os.path.join(project_root, "data")
    jsonl_path = os.path.join(project_root, "knowledge_base_embedded.jsonl")
    npy_path = os.path.join(project_root, "embeddings.npy")
    db_storage_path = os.path.join(project_root, "chroma_db")

    if not os.path.exists(jsonl_path) or not os.path.exists(npy_path):
        print("[ERROR] Missing required inputs. Please run your embedding generation script first.")
        return

    print("[PROCESSING] Loading pre-computed matrix from embeddings.npy...")
    embeddings_matrix = np.load(npy_path)
    embeddings_list = embeddings_matrix.tolist()

    ids = []
    documents = []
    metadatas = []

    # Read and parse your embedded text lines
    with open(jsonl_path, "r", encoding="utf-8") as f:
        jsonl_records = [json.loads(line) for line in f if line.strip()]

    # Open plans.csv separately to inspect the headers and rows directly
    csv_file_path = os.path.join(data_dir, "plans.csv")
    csv_rows = []
    if os.path.exists(csv_file_path):
        with open(csv_file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Strip spaces and force headers to lowercase to fix naming issues
            reader.fieldnames = [field.strip().lower() for field in reader.fieldnames] if reader.fieldnames else None
            print(f"[DIAGNOSTIC] Detected CSV Headers: {reader.fieldnames}")
            for row in reader:
                csv_rows.append(row)

    print("[PROCESSING] Re-indexing chunks with accurate network tier extraction...")
    for idx, record in enumerate(jsonl_records):
        chunk_text = record["text"]
        source_file_lower = record["source_file"].lower()
        
        ids.append(record["id"])
        documents.append(chunk_text)
        
        text_lower = chunk_text.lower()
        network_tier_val = "shared"

        if "plans.csv" in source_file_lower:
            # Map back to the corresponding row in our parsed csv rows list
            if idx < len(csv_rows):
                row = csv_rows[idx]
                # Look for column keys under standard names
                network_tier_val = row.get("network_tier", row.get("network", "unknown")).strip().lower()
        else:
            # Dynamically tag unstructured files so filtering succeeds
            if "gold" in text_lower:
                network_tier_val = "gold"
            elif "bronze" in text_lower:
                network_tier_val = "bronze"
            elif "silver" in text_lower or "physical therapy" in text_lower:
                network_tier_val = "silver"

        metadatas.append({
            "source_file": record["source_file"],
            "source_type": record["source_type"],
            "plan_type": record["plan_type"],
            "section": record["section"],
            "ingested_at": record["ingested_at"],
            "network_tier": network_tier_val
        })

    # Initialize Chroma client and reset collection data
    client = chromadb.PersistentClient(path=db_storage_path)
    print("[PROCESSING] Resetting old database records to clear 'unknown' tags...")
    try:
        client.delete_collection(name="coverage_kb")
    except:
        pass
    collection = client.create_collection(name="coverage_kb")

    total_records = len(ids)
    batch_size = 100
    print(f"[PROCESSING] Streaming database uploads in batches...")
    for i in range(0, total_records, batch_size):
        end_idx = min(i + batch_size, total_records)
        collection.upsert(
            ids=ids[i:end_idx],
            embeddings=embeddings_list[i:end_idx],
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx]
        )

    print("\n" + "="*50)
    print(f"[SUCCESS] Re-indexing complete! New tags are active.")
    print(f" -> Active Collection Count: {collection.count()}")
    print("="*50 + "\n")

if __name__ == "__main__":
    batch_upsert_to_chroma()