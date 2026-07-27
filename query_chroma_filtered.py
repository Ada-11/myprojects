import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

def run_filtered_semantic_search():
    # 1. Coordinate target system path variables
    project_root = "/Users/ada/myprojects/my-first-app"
    db_storage_path = os.path.join(project_root, "chroma_db")
    output_md_path = os.path.join(project_root, "vector_query_test.md")

    if not os.path.exists(db_storage_path):
        print(f"[ERROR] Could not find the database folder directory at: {db_storage_path}")
        return

    # 2. Ingest local model and encode search terms
    print("[PROCESSING] Loading local all-MiniLM-L6-v2 model for search embedding...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    query_text = "Is physical therapy covered under the Silver plan?"
    print(f"[PROCESSING] Generating vector coordinates for query string: '{query_text}'")
    query_vector_list = model.encode(query_text).tolist()

    # 3. Connect to persistent storage client layer
    client = chromadb.PersistentClient(path=db_storage_path)
    collection = client.get_collection(name="coverage_kb")

    # --- SEARCH UNFILTERED WAVE ---
    print("[PROCESSING] Querying baseline Unfiltered results (n_results=5)...")
    unfiltered_results = collection.query(
        query_embeddings=[query_vector_list],
        n_results=5
    )

    # --- SEARCH METADATA-FILTERED WAVE ---
    # Note: Based on your plans.csv data profile layout, the Silver plan row 
    # uses 'HMO' as its coverage plan_type column tag value.
    target_filter_type = "HMO" 
    print(f"[PROCESSING] Querying Filtered results scope restricted to plan_type: '{target_filter_type}'...")
    
    filtered_results = collection.query(
        query_embeddings=[query_vector_list],
        n_results=5,
        where={"plan_type": target_filter_type} # Injected metadata scope filter parameter
    )

    # 4. LOG COMPREHENSIVE PAIR LOGS INTO MARKDOWN
    print(f"[PROCESSING] Appending verification matrix tables to: {output_md_path}")
    with open(output_md_path, "w", encoding="utf-8") as md_file:
        md_file.write(f"# Comprehensive Vector Search Verification Audit Logs\n\n")
        md_file.write(f"**Target Core Query:** `{query_text}`\n\n")
        
        # ----------------------------------------------------
        # TABLE A: UNFILTERED RESULTS RENDERING
        # ----------------------------------------------------
        md_file.write(f"## 1. Unfiltered Baseline Query (Top 5 Matches)\n")
        md_file.write(f"Matches across all available indexed document source types without restrictions.\n\n")
        md_file.write("| Rank | Score | Source File | Section / Plan Type | Document Text Content |\n")
        md_file.write("| :--- | :--- | :--- | :--- | :--- |\n")
        
        un_docs = unfiltered_results["documents"][0]
        un_metas = unfiltered_results["metadatas"][0]
        un_dists = unfiltered_results["distances"][0]
        
        for idx, (doc, meta, dist) in enumerate(zip(un_docs, un_metas, un_dists), start=1):
            clean_doc = doc.replace('\n', ' ').strip()
            md_file.write(f"| #{idx} | {dist:.4f} | {os.path.basename(meta['source_file'])} | {meta['section'].upper()} / {meta['plan_type']} | {clean_doc} |\n")

        md_file.write("\n" + "="*80 + "\n\n")

        # ----------------------------------------------------
        # TABLE B: FILTERED RESULTS RENDERING
        # ----------------------------------------------------
        md_file.write(f"## 2. Metadata-Filtered Query (Scope Constraint: `plan_type == {target_filter_type}`)\n")
        md_file.write(f"Verification Check: All rows must match the plan_type criteria context window explicitly.\n\n")
        md_file.write("| Rank | Score | Source File | Section / Plan Type | Document Text Content |\n")
        md_file.write("| :--- | :--- | :--- | :--- | :--- |\n")
        
        f_docs = filtered_results["documents"][0]
        f_metas = filtered_results["metadatas"][0]
        f_dists = filtered_results["distances"][0]
        
        for idx, (doc, meta, dist) in enumerate(zip(f_docs, f_metas, f_dists), start=1):
            clean_doc = doc.replace('\n', ' ').strip()
            md_file.write(f"| #{idx} | {dist:.4f} | {os.path.basename(meta['source_file'])} | {meta['section'].upper()} / {meta['plan_type']} | {clean_doc} |\n")

    print(f"[SUCCESS] Filtered verification test query phase complete! Check logs inside your markdown file folder path.")

if __name__ == "__main__":
    run_filtered_semantic_search()