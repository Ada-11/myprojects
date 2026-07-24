import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer

def embed_entire_knowledge_base():
    # 1. Define strict paths pointing to your project folders
    project_root = "/Users/ada/myprojects/my-first-app"
    input_jsonl_path = os.path.join(project_root, "knowledge_base.jsonl")
    output_jsonl_path = os.path.join(project_root, "knowledge_base_embedded.jsonl")
    npy_output_path = os.path.join(project_root, "embeddings.npy")

    if not os.path.exists(input_jsonl_path):
        print(f"[ERROR] Could not locate source file at: {input_jsonl_path}")
        return

    # 2. Initialize the local assignment model
    print("[PROCESSING] Loading local all-MiniLM-L6-v2 transformer model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Arrays to temporarily store data for verification export stages
    updated_records = []
    parallel_vectors_list = []

    # 3. Read and loop through each line / chunk from your knowledge base
    print("[PROCESSING] Reading lines and computing individual chunk vectors...")
    with open(input_jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            if not line.strip():
                continue
                
            # Parse line string to active Python dictionary object
            record = json.loads(line)
            chunk_text = record["text"]

            # Generate embedding vector array matrix (Local execution)
            vector_numpy = model.encode(chunk_text)
            vector_list = vector_numpy.tolist()

            # Store variant A: as an embedding field on the chunk
            record["embedding"] = vector_list
            updated_records.append(record)

            # Store variant B: save into a parallel tracking index container list
            parallel_vectors_list.append(vector_numpy)

    if not updated_records:
        print("[WARNING] Zero records detected inside source data layout. Aborting process.")
        return

    # 4. Save updated embedded JSONL file tracking
    print(f"[PROCESSING] Writing integrated field entries to: {output_jsonl_path}")
    with open(output_jsonl_path, "w", encoding="utf-8") as out_jsonl:
        for record in updated_records:
            out_jsonl.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 5. Verification: Convert tracking list to a true numpy array matrix and save binary npy file
    print(f"[PROCESSING] Packing tracking array layer matrices for NumPy validation...")
    embeddings_matrix = np.array(parallel_vectors_list, dtype=np.float32)
    
    # Export verification file binary write
    np.save(npy_output_path, embeddings_matrix)

    print("\n" + "="*60)
    print("[SUCCESS] Teacher assignment loop task executed successfully!")
    print(f" -> Processed Chunk Count: {len(updated_records)} rows processed.")
    print(f" -> Matrix Dimensions:    {embeddings_matrix.shape} (Chunks x Dimensions)")
    print(f" -> Saved Vector Field:   {output_jsonl_path}")
    print(f" -> Saved Binary Check:   {npy_output_path}")
    print("="*60)

if __name__ == "__main__":
    embed_entire_knowledge_base()