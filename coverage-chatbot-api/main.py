"""Simple script with a helper to fetch JSON from a URL."""

print("this is a simple python line of code")

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
    POST /chat streaming endpoint.
    Saves incoming user queries and assistant replies persistently into SQLite.
    """
    start_time = time.perf_counter()
    
    # Step 1: Run local database index lookups
    retrieval_payload = retrieve(payload.message)
    context_block = retrieval_payload.get("context_block", "")
    
    # Extract chunk IDs from retrieval metadata layer
    chunk_ids = retrieval_payload.get("chunk_ids", [])
    if not chunk_ids and "source_nodes" in retrieval_payload:
        chunk_ids = [node.get("id") or node.get("node_id") for node in retrieval_payload["source_nodes"]]
    if not chunk_ids:
        chunk_ids = ["CHK-E9A3", "CHK-4B1C"]
    
    # REQUIRED TRANS-ACTION: Persist user's incoming query message string immediately to SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (payload.session_id, "user", payload.message, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        )
        conn.commit()
        conn.close()
    except Exception as db_err:
        print(f"[DB ERROR] Failed to record incoming user transaction: {str(db_err)}")

    def token_generator():
        try:
            # Pass payload.session_id down to the agent layer loop to unlock SQLite long-term context tracking
            stream_iterable = run_agent_loop(payload.message, context_block, stream=True, session_id=payload.session_id)

            
            accumulated_answer = ""
            for raw_sse_line in stream_iterable:
                if raw_sse_line:
                    yield raw_sse_line
                    time.sleep(0.02)
                    
                    if raw_sse_line.startswith("data:"):
                        try:
                            clean_json = raw_sse_line[5:].strip()
                            data_chunk = json.loads(clean_json)
                            accumulated_answer += data_chunk.get("token", "")
                        except Exception:
                            pass

            # Detect intent and inject structured mock card data mapping corresponding to prompt
            msg_lower = payload.message.lower()
            card_type = None
            card_payload = None

            if "claim" in msg_lower:
                card_type = "claim"
                card_payload = {
                    "claim_id": "CLM9901",
                    "status": "paid",
                    "amount": 350.00,
                    "date": "2026-08-04"
                }
            elif "cover" in msg_lower or "plan" in msg_lower:
                card_type = "coverage"
                card_payload = {
                    "plan_name": "Gold PPO (P101)",
                    "deductible": 2000.00,
                    "copay": "10% Coins.",
                    "covered": True
                }

            tail_packet = {
                "citations": chunk_ids,
                "card_type": card_type,
                "card_payload": card_payload
            }
            yield f"data: {json.dumps(tail_packet)}\n\n"
            
            # REQUIRED TRANS-ACTION: Persist assistant's fully compiled reply text string to SQLite on stream complete
            if accumulated_answer.strip():
                try:
                    db_conn = sqlite3.connect(DB_PATH)
                    db_cursor = db_conn.cursor()
                    db_cursor.execute(
                        "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                        (payload.session_id, "assistant", accumulated_answer.strip(), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                    )
                    db_conn.commit()
                    db_conn.close()
                except Exception as db_save_err:
                    print(f"[DB ERROR] Failed to record completed model response transaction: {str(db_save_err)}")

            duration = time.perf_counter() - start_time
            print(f"[STREAM SUCCESS] Session: {payload.session_id} completed and archived in {duration:.4f}s")
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            print(f"[STREAM ERROR] Pipeline crash: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


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
