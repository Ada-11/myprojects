import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

def run_semantic_search():
    project_root = "/Users/ada/myprojects/my-first-app"
    db_storage_path = os.path.join(project_root, "chroma_db")

    if not os.path.exists(db_storage_path):
        print(f"[ERROR] Could not find the database folder directory at: {db_storage_path}")
        return

    print("[PROCESSING] Loading local all-MiniLM-L6-v2 model for search embedding...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    query_text = "Is physical therapy covered under the Silver plan?"
    print(f"[PROCESSING] Generating vector coordinates for query string: '{query_text}'")
    query_vector_list = model.encode(query_text).tolist()

    client = chromadb.PersistentClient(path=db_storage_path)
    collection = client.get_collection(name="coverage_kb")

    # CORRECTED FILTER: Swapped from coverage_type to network_tier lookup target
    print("[PROCESSING] Running collection.query() with network_tier: 'silver' filter...")
    query_results = collection.query(
        query_embeddings=[query_vector_list],
        n_results=5,
        where={"network_tier": "silver"}
    )

    print("\n" + "="*70)
    print(f"METADATA-FILTERED RESULTS FOR: '{query_text}' (network_tier == silver)")
    print("="*70)

    documents = query_results["documents"][0]
    metadatas = query_results["metadatas"][0]
    distances = query_results["distances"][0]

    for idx, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), start=1):
        print(f"Match #{idx} [Distance Core Score: {dist:.4f}]")
        print(f" -> Source File: {os.path.basename(meta['source_file'])}")
        print(f" -> Section / Network Tier: {meta['section'].upper()} / {meta['network_tier'].upper()}")
        print(f" -> Extracted Text Chunk: \"{doc.strip()}\"")
        print("-" * 70)

if __name__ == "__main__":
    run_semantic_search()