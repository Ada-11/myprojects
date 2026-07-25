import os
import time
from pinecone import Pinecone, ServerlessSpec

def initialize_pinecone_index():
    # Provide your unique dashboard API key credential here
    PINECONE_API_KEY = "YOUR_API_KEY_HERE" 
    
    if PINECONE_API_KEY == "YOUR_API_KEY_HERE":
        print("[ERROR] Please replace 'YOUR_API_KEY_HERE' with your real key from app.pinecone.io")
        return

    print("[PROCESSING] Connecting to official Pinecone Client SDK cloud engine...")
    pc = Pinecone(api_key=PINECONE_API_KEY)

    index_name = "coverage-kb"  # Pinecone forces lowercase and hyphens

    # FIXED: Correctly iterate over the index configurations returned by the client method call
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    
    if index_name not in existing_indexes:
        print(f"[PROCESSING] Creating Serverless Index: '{index_name}'...")
        
        # Top-level client index generation wrapper call
        pc.create_index(
            name=index_name,
            dimension=384,          # Matches all-MiniLM-L6-v2 vector array footprint length
            metric="cosine",        # Standard semantic matching vector formula
            spec=ServerlessSpec(
                cloud="aws",        # Free-tier serverless baseline platform layer
                region="us-east-1"  # Default standard serverless hosting zone
            )
        )
        print("[INFO] Index creation signal sent. Waiting for initialization...")
        
        # Wait a few seconds for cloud container assignment provisioning
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
    else:
        print(f"[INFO] Index '{index_name}' already exists in your cloud dashboard portfolio.")

    # 3. VERIFICATION: Target the active empty index to confirm total records
    print("\n" + "="*50)
    print("[VERIFICATION] Running remote server checks...")
    
    index_description = pc.describe_index(index_name)
    print(f" -> Remote Host Name: {index_description.host}")
    print(f" -> Dimensionality Cap: {index_description.dimension} float points per vector")
    
    # Establish connection layer directly to index to read current footprint stats
    index_client = pc.Index(index_name)
    index_stats = index_client.describe_index_stats()
    
    print(f" -> Confirmed Vector Count: {index_stats['total_vector_count']} records inside cluster.")
    print("="*50 + "\n")
    print("[SUCCESS] Pinecone comparison node is stood up and completely empty!")

if __name__ == "__main__":
    initialize_pinecone_index()