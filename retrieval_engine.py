import os
import csv
import json
import uuid
from datetime import datetime, timezone
import chromadb
from sentence_transformers import SentenceTransformer

# Setup paths targeting your main project directory
PROJECT_ROOT = "/Users/ada/myprojects/my-first-app"
DB_STORAGE_PATH = os.path.join(PROJECT_ROOT, "chroma_db")
CSV_PATH = os.path.join(PROJECT_ROOT, "data", "plans.csv")

def classify_question(question: str) -> str:
    """
    Lightweight rule-based question classifier.
    Labels questions as 'structured', 'unstructured', or 'both'.
    """
    q_lower = question.lower()
    
    # Intent tracking lists
    structured_keywords = ["deductible", "premium", "monthly cost", "annual limit", "how much", "premium cost", "plan cost"]
    unstructured_keywords = ["covered", "procedure", "therapy", "exclusion", "not covered", "pre-authorization", "approved", "treatment"]
    
    has_struct = any(kw in q_lower for kw in structured_keywords) or "plan" in q_lower
    has_unstruct = any(kw in q_lower for kw in unstructured_keywords)
    
    if has_struct and has_unstruct:
        return "both"
    elif has_struct:
        return "structured"
    else:
        return "unstructured"

def sql_lookup(question: str) -> list:
    """
    Simulates structured data layout retrieval from the plans dataset.
    Translates question intent into clean relational data row lookups.
    """
    q_lower = question.lower()
    results = []
    
    if not os.path.exists(CSV_PATH):
        return [{"error": "plans.csv dataset missing from directory"}]

    # Determine which plan tier the user is explicitly targeting
    target_tier = None
    if "gold" in q_lower:
        target_tier = "gold"
    elif "silver" in q_lower:
        target_tier = "silver"
    elif "bronze" in q_lower:
        target_tier = "bronze"

    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [field.strip().lower() for field in reader.fieldnames] if reader.fieldnames else None
        
        for row in reader:
            tier_val = row.get("network_tier", row.get("network", "")).strip().lower()
            
            # SQL-style filtering condition: WHERE network_tier == target_tier
            if target_tier and tier_val != target_tier:
                continue
                
            # Isolate columns to simulate targeted SELECT projections
            results.append({
                "plan_name": row.get("plan_name", "Unknown"),
                "monthly_premium": f"${row.get('monthly_premium', '0')}",
                "annual_deductible": f"${row.get('annual_deductible', '0')}",
                "copay_pct": f"{row.get('copay_pct', '0')}%",
                "coverage_type": row.get("coverage_type", "N/A"),
                "network_tier": tier_val.upper()
            })
            
    return results

def vector_lookup(question: str, limit: int = 5) -> list:
    """
    Executes a semantic vector search query against the local Chroma collection.
    Embeds the user's question and retrieves the top-5 relevant policy chunks.
    """
    # Safety check for database existence before triggering model
    if not os.path.exists(DB_STORAGE_PATH):
        print(f"[ERROR] Persistent database directory not found at: {DB_STORAGE_PATH}")
        return []
        
    # 1. Initialize the local assignment transformer model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # 2. Embed the question text phrase into a list vector mapping profile
    query_vector = model.encode(question).tolist()
    
    # 3. Establish a connection to your local persistent storage client layer
    client = chromadb.PersistentClient(path=DB_STORAGE_PATH)
    
    try:
        collection = client.get_collection(name="coverage_kb")
        
        # 4. Query the vector database for the top-5 relevant policy chunks
        query_results = collection.query(
            query_embeddings=[query_vector],
            n_results=limit
        )
        
        # 5. Restructure the raw dictionary output into a clean, trackable list layout
        formatted_results = []
        if query_results["documents"] and query_results["documents"][0]:
            docs = query_results["documents"][0]
            metas = query_results["metadatas"][0]
            dists = query_results["distances"][0]
            
            for d, m, dist in zip(docs, metas, dists):
                formatted_results.append({
                    "text": d.strip(),
                    "source_file": os.path.basename(m.get("source_file", "unknown")),
                    "source_type": m.get("source_type", "unstructured"),
                    "plan_type": m.get("plan_type", "unknown"),
                    "section": m.get("section", "coverage").upper(),
                    "score": round(float(dist), 4) # Cosine distance calculation metric score
                })
                
        return formatted_results
    except Exception as e:
        print(f"[CRITICAL ERROR] Vector index lookup failure: {str(e)}")
        return []

def retrieve(question: str) -> dict:
    """
    Unified hybrid retrieval coordinator. 
    Routes queries to SQL, Vector, or both, then merges and de-duplicates 
    all outputs into a single context block string.
    """
    # 1. Classify the user query intent profile
    classification = classify_question(question)
    
    structured_raw = []
    unstructured_raw = []
    
    # 2. Selective routing execution loop
    if classification == "structured":
        structured_raw = sql_lookup(question)
    elif classification == "unstructured":
        unstructured_raw = vector_lookup(question, limit=2)
    elif classification == "both":
        structured_raw = sql_lookup(question)
        unstructured_raw = vector_lookup(question, limit=2)
        
    # 3. MERGE & DE-DUPLICATE RESULTS INTO ONE CONTEXT BLOCK
    context_lines = []
    seen_texts = set()  # Mathematical set to catch duplicate text strings instantly
    
    # A. Process and append structured relational row metrics
    if structured_raw:
        context_lines.append("--- STRUCTURED PLAN METRICS (DATABASE LOOKUP) ---")
        for row in structured_raw:
            # Flatten row columns into a singular, crisp fact text summary sentence
            fact_string = (
                f"Plan: {row['plan_name']} | "
                f"Monthly Premium: {row['monthly_premium']} | "
                f"Annual Deductible: {row['annual_deductible']} | "
                f"Copay Coinsurance: {row['copay_pct']} | "
                f"Tier Group: {row['network_tier']}"
            )
            if fact_string not in seen_texts:
                seen_texts.add(fact_string)
                context_lines.append(fact_string)
                
    # B. Process and append unstructured semantic document fragments
    if unstructured_raw:
        if context_lines:
            context_lines.append("")  # Insert a clean layout line gap separator
        context_lines.append("--- UNSTRUCTURED POLICY DOCUMENT SECTIONS (VECTOR LOOKUP) ---")
        
        for idx, match in enumerate(unstructured_raw, start=1):
            text_payload = match['text'].strip()
            
            # Skip if an identical paragraph vector was already captured
            if text_payload not in seen_texts:
                seen_texts.add(text_payload)
                # Form a metadata-tagged text reference block
                context_lines.append(
                    f"[Ref #{idx} | Source: {match['source_file']} | Section: {match['section']}]\n"
                    f"{text_payload}"
                )
                context_lines.append("")  # Spacer layout break between policy paragraphs

    # 4. Collapse lines list down into one solid string payload canvas
    final_context_block = "\n".join(context_lines).strip()
    
    # Handle absolute empty fallbacks gracefully
    if not final_context_block:
        final_context_block = "No matching insurance policy data chunks or relational metrics could be found."

    # Return the clean payload package object matching your test pipeline requirements
    return {
        "question": question,
        "classification": classification,
        "structured_data": structured_raw,
        "unstructured_data": unstructured_raw,
        "context_block": final_context_block
    }

if __name__ == "__main__":
    # Define the 10 distinct, realistic customer service queries
    test_cases = [
        "What is my annual deductible under the Gold PPO plan?",
        "Is physical therapy covered by my insurance policy?",
        "Show me the monthly premium costs for all available plans.",
        "Are cosmetic surgeries listed as exclusions under the Silver tier?",
        "What is the copay percentage for the Bronze HMO choice?",
        "How do I file a medical claim or get an update on billing error codes?",
        "What are the premium and deductible costs for the Silver HMO plan?",
        "Is outpatient speech evaluation covered under the Silver plan?",
        "Does the Bronze plan have a higher monthly cost than the Gold plan?",
        "Are experimental clinical drug trials completely restricted or denied?"
    ]
    
    output_md_path = os.path.join(PROJECT_ROOT, "retrieval_test_results.md")
    print(f"[PROCESSING] Commencing verification testing across {len(test_cases)} evaluation nodes...")
    
    with open(output_md_path, "w", encoding="utf-8") as out:
        out.write("# Hybrid Retrieval Routing Engine Test Audit Report\n\n")
        out.write(f"**Verification Execution Timestamp:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`\n")
        out.write(f"**Active Chroma Storage Node:** `{DB_STORAGE_PATH}`\n\n")
        
        for idx, question in enumerate(test_cases, start=1):
            print(f" -> Executing evaluation node #{idx}: '{question[:40]}...'")
            
            # Execute unified hybrid routing lookup
            response = retrieve(question)
            
            # 1. QUESTION TEXT LOGGING REQUIREMENT
            out.write(f"### Test Case #{idx}\n")
            out.write(f"**Question:** {response['question']}\n\n")
            
            # 2. CLASSIFICATION LABEL LOGGING REQUIREMENT
            out.write(f"**Classification:** `{response['classification'].upper()}`\n\n")
            
            # 3. RETRIEVED CONTEXT LOGGING REQUIREMENT (Merged & De-duplicated Excerpt)
            out.write("**Retrieved Context:**\n")
            out.write("```text\n")
            out.write(f"{response['context_block']}\n")
            out.write("```\n\n")
            
            # Formatting line separator wrapper between audit blocks
            out.write("-" * 85 + "\n\n")
            
    print(f"[SUCCESS] Audit completed successfully! Output data matrix saved to: {output_md_path}")