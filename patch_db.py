import sqlite3

DB_PATH = "/Users/ada/myprojects/my-first-app/coverage-chatbot-api/coverage.db"

def manual_table_patch():
    print("🛠️ Opening database connection layer...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🛠️ Creating 'token_usage' logging structure table if missing...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            estimated_cost REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("🎉 TABLE STRUCTURE 'token_usage' SUCCESSFULLY PROVISIONED ON DISK!")

if __name__ == "__main__":
    manual_table_patch()
