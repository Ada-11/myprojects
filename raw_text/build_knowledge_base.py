import os
import re
import csv
import json
import uuid
from datetime import datetime, timezone
from langchain_text_splitters import RecursiveCharacterTextSplitter

TIMESTAMP_NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

SENTENCE_SAFE_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len
)

SECTION_PATTERNS = {
    "exclusions": re.compile(r'(?i)\b(exclusions|not covered|limitations|out-of-pocket maximums|restricted|denied)\b'),
    "claims": re.compile(r'(?i)\b(claims|reimbursement|adjudication|billing|appeal|error code)\b'),
    "enrollment": re.compile(r'(?i)\b(enrollment|apply|waive|member id|subscriber|dependent)\b'),
    "coverage": re.compile(r'(?i)\b(coverage|benefits|covered services|copay|deductible|premium|ppo|hmo)\b')
}

def determine_section_type(text_content, default_fallback="coverage"):
    for section_name, pattern in SECTION_PATTERNS.items():
        if pattern.search(text_content):
            return section_name
    return default_fallback


def extract_chunks_safely(text_content, fallback_section):
    header_regex = r'(?im)^[#\s]*(exclusions|covered services|claims process|enrollment form)\s*[:\-]*\s*$'
    parts = re.split(header_regex, text_content)
    
    if len(parts) <= 1:
        return SENTENCE_SAFE_SPLITTER.split_text(text_content)
        
    final_chunks = []
    
    first_part = parts.strip()
    if first_part:
        final_chunks.extend(SENTENCE_SAFE_SPLITTER.split_text(first_part))
        
    for i in range(1, len(parts), 2):
        heading_title = parts[i].strip().lower()
        clause_body = parts[i+1] if (i+1) < len(parts) else ""
        full_block = f"[{heading_title.upper()}]\n{clause_body.strip()}"
        
        if heading_title == "exclusions" or "not covered" in heading_title:
            final_chunks.append(full_block)
        else:
            final_chunks.extend(SENTENCE_SAFE_SPLITTER.split_text(full_block))
            
    return final_chunks


def process_knowledge_base(output_jsonl_path="knowledge_base.jsonl"):
    records_written, structured_count, unstructured_count = 0, 0, 0

    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, "/Users/ada/myprojects/my-first-app/data/plans.csv")
    
    # CHANGED: Explicitly targets the project root directory folder for file creation
    target_root_destination = "/Users/ada/myprojects/my-first-app/knowledge_base.jsonl"
    
    print(f"[DIAGNOSTIC] Looking for plans.csv at: {csv_file}")
    print(f"[DIAGNOSTIC] Files present in this folder: {os.listdir(script_dir)}")

    with open(target_root_destination, "w", encoding="utf-8") as jsonl_file:

        # === LAYER 1: STRUCTURED PLANS ===
        if os.path.exists(csv_file):
            print(f"[PROCESSING] Ingesting structured rows from live file: {csv_file}...")
            with open(csv_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                reader.fieldnames = [field.strip() for field in reader.fieldnames] if reader.fieldnames else None
                for row in reader:
                    name = row.get('plan_name', 'Unknown Plan').strip()
                    premium = row.get('monthly_premium', '0').strip()
                    deductible = row.get('annual_deductible', '0').strip()
                    coins = row.get('copay_pct', '0').strip()
                    network = row.get('network_tier', 'unknown').strip().lower()
                    
                    formatted_text = f"{name}: ${premium}/month premium, ${deductible} deductible, {coins}% coinsurance, network: {network}"
                    
                    record = {
                        "id": str(uuid.uuid4()),
                        "text": formatted_text,
                        "source_file": csv_file,
                        "source_type": "structured",
                        "plan_type": row.get('coverage_type', 'PPO').strip(),
                        "section": "coverage",
                        "ingested_at": TIMESTAMP_NOW
                    }
                    jsonl_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                    records_written += 1
                    structured_count += 1
        else:
            print(f"[WARNING] plans.csv not found at {csv_file}. Skipping structured layout.")

        # === LAYER 2: UNSTRUCTURED TEXT CODES ===
        unstructured_targets = [
            ("/Users/ada/myprojects/my-first-app/raw_text/benefits.txt", "coverage", "PPO/HMO Mixed"),
            ("/Users/ada/myprojects/my-first-app/raw_text/claims_process.txt", "claims", "Cross-Plan Operational"),
            ("/Users/ada/myprojects/my-first-app/raw_text/enrollment.txt", "enrollment", "Account Management")
        ]

        for base_filename, fallback_section, plan_type in unstructured_targets:
            filename = os.path.join(script_dir, base_filename)
            
            if not os.path.exists(filename):
                print(f"[INFO] File not found: {filename}. Skipping.")
                continue
                
            print(f"[PROCESSING] Running sentence-safe segmentation on: {filename}...")
            with open(filename, "r", encoding="utf-8") as f:
                raw_text = f.read()
                
            if not raw_text.strip():
                print(f"[WARNING] File is empty: {filename}. Skipping.")
                continue
                
            chunks = extract_chunks_safely(raw_text, fallback_section)
            
            for chunk in chunks:
                clean_chunk = chunk.strip()
                if not clean_chunk:
                    continue
                    
                detected_section = determine_section_type(clean_chunk, default_fallback=fallback_section)
                
                record = {
                    "id": str(uuid.uuid4()),
                    "text": clean_chunk,
                    "source_file": filename,
                    "source_type": "unstructured",
                    "plan_type": plan_type,
                    "section": detected_section,
                    "ingested_at": TIMESTAMP_NOW
                }
                jsonl_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                records_written += 1
                unstructured_count += 1

    print("\n" + "="*50)
    print(f"[SUCCESS] Sentence-safe knowledge base generated!")
    print(f" -> Structured Records Ingested:  {structured_count}")
    print(f" -> Unstructured Chunks Ingested: {unstructured_count}")
    print(f"[SUCCESS] Total lines saved to knowledge_base.jsonl: {records_written}")
    print("="*50)


if __name__ == "__main__":
    process_knowledge_base()