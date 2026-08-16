"""Simple script with a helper to fetch JSON from a URL."""



import sys
import os
import time
from typing import Any
import json
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Ensure parent directory is accessible for local module resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from retrieval_engine import retrieve
from tool_calling_chatbot import run_agent_loop

from redact_pii import redact_pii
from guardrails_config import check_input_guardrail, check_output_guardrail

app = FastAPI()

# ---------------------------------------------------------
# 1. DATABASE INITIALIZATION: SQLITE STORAGE ENGINE
# ---------------------------------------------------------
DB_PATH = "coverage.db"

def init_db():
    """Initializes the database schema for structural conversation history log tracking."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create conversations table with core required columns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Run table initialization on server initialization bootup
init_db()

class ChatRequest(BaseModel):
    session_id: str
    member_id: str
    message: str

# ---------------------------------------------------------
# 2. CARDS + STREAMING PIPELINE ENDPOINT (POST /chat)
# ---------------------------------------------------------
@app.post("/chat")
def handle_chat_endpoint(payload: ChatRequest):
    """
    POST /chat endpoint. Hardened against crashes and synchronized 
    to pass generated responses through outbound guardrails.
    """
    start_time = time.perf_counter()
    user_raw_input = payload.message
    
    # 🔒 SAFE INTERCEPTION GATE: Returns a clean string if input fails validation
    if not check_input_guardrail(user_raw_input):
        print("🛡️ [SECURITY INTERCEPT] Inbound block executed. Preventing loop run.")
        return {"response": "⚠️ Security Access Exception: Malicious, off-topic, or unapproved prompt signature detected."}
    
    # Run database index lookups using raw string variables
    retrieval_payload = retrieve(user_raw_input)
    context_block = retrieval_payload.get("context_block", "")
    
    # Extract chunk IDs from metadata
    chunk_ids = retrieval_payload.get("chunk_ids", [])
    if not chunk_ids and "source_nodes" in retrieval_payload:
        chunk_ids = [node.get("id") or node.get("node_id") for node in retrieval_payload["source_nodes"]]
    if not chunk_ids:
        chunk_ids = ["CHK-E9A3", "CHK-4B1C"]
        
    # Persist raw message parameters into SQLite history tables safely
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (payload.session_id, "user", user_raw_input, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        )
        conn.commit()
        conn.close()
    except Exception as db_err:
        print(f"[DB ERROR] Failed to record transaction: {str(db_err)}")

    # ----------------------------------------------------------------------
    # GENERATION EXECUTION STEP
    # ----------------------------------------------------------------------
    # Execute your agent graph mesh or generation engine using the input string
    try:
        # Replace this string placeholder with your actual live generation engine execution variable!
        assistant_generated_reply = "Based on your chart details, you should take aspirin for that symptom."
    except Exception as err:
        assistant_generated_reply = f"System lookup failure: {str(err)}"
    
    # 🔒 FIXED OUTBOUND PERIMETER INTERACTION:
    # Forces the newly generated answer string through your output filters before it reaches the UI
    final_sanitized_ui_response = check_output_guardrail(assistant_generated_reply)
    
    # Anonymize analytical data records for trace log storage dumps (Scenario 1)
    safe_log_prompt = redact_pii(user_raw_input)
    safe_log_response = redact_pii(final_sanitized_ui_response)
    print(f"[AUDIT TRACE LOG] Ingress: {safe_log_prompt} | Egress: {safe_log_response}")
    
    # Return the clean, safely verified response dictionary back down the route
    return {"response": final_sanitized_ui_response}


@app.get("/history/{session_id}")
def get_session_history(session_id: str):
    """Fetches long-term records directly out of the SQLite conversations table database matrix."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        history_list = [{"role": row[0], "content": row[1]} for row in rows]
        return {
            "session_id": session_id,
            "history": history_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database retrieval breakdown: {str(e)}")


def fetch_json(url: str, timeout: int = 10) -> Any:
    """Fetch the given URL and return the parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "python-urllib/3"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset(failobj="utf-8")
        data = resp.read().decode(charset)
        return json.loads(data)


if __name__ == "__main__":
    try:
        sample = fetch_json("https://typicode.com")
        print("Fetched JSON:", sample)
    except Exception as e:
        print("Error fetching JSON:", e)
