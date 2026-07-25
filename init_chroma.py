import os
import chromadb

def initialize_persistent_chroma():
    # Define your project folder and the path to save the database files
    project_root = "/Users/ada/myprojects/my-first-app"
    db_storage_path = os.path.join(project_root, "chroma_db")
    
    print(f"[PROCESSING] Initializing Persistent Chroma Client at: {db_storage_path}")
    
    # 1. Create a persistent client (saves data directly to your hard drive)
    client = chromadb.PersistentClient(path=db_storage_path)

    # 2. Safely create or retrieve the collection requirement
    collection_name = "coverage_kb"
    print(f"[PROCESSING] Creating collection: '{collection_name}'...")
    
    try:
        # Using get_or_create_collection prevents errors if you run this script multiple times
        collection = client.get_or_create_collection(name=collection_name)
        print(f"[SUCCESS] Collection '{collection_name}' is active.")
    except Exception as e:
        print(f"[ERROR] Failed to handle collection creation: {str(e)}")
        return

    # 3. VERIFICATION: Confirm the collection exists (List & Get by name)
    print("\n" + "="*50)
    print("[VERIFICATION] Running database checks...")
    
    # Check A: List all collections currently saved in the database folder
    all_collections = client.list_collections()
    # Pull names from the collection objects returned by Chroma
    collection_names = [col.name for col in all_collections]
    print(f" -> Active Collections List: {collection_names}")

    # Check B: Retrieve the specific collection by its name to ensure it is healthy
    try:
        verified_collection = client.get_collection(name=collection_name)
        print(f" -> Confirm Status: Found '{verified_collection.name}' by explicit name lookup.")
        print(f" -> Total records inside collection right now: {verified_collection.count()}")
    except Exception as e:
        print(f" -> Confirm Status: [FAILED] Could not look up collection by name. Error: {str(e)}")
        
    print("="*50 + "\n")

if __name__ == "__main__":
    initialize_persistent_chroma()