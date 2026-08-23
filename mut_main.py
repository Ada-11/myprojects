import sys
import os
import time
import json
import sqlite3
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, List
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# --- INITIALIZE ENVIRONMENT & OBSERVABILITY ---
load_dotenv()
from langfuse import Langfuse
langfuse = Langfuse()

# --- PROJECT MODULE IMPORTS ---
from retrieval_engine import retrieve
from redact_pii import redact_pii
from guardrails_config import check_input_guardrail, check_output_guardrail
from token_utils import count_tokens

app = FastAPI()

# Configuration: Path to your SQLite DB
DB_PATH = "coverage-chatbot-api/coverage.db"

# ---------------------------------------------------------
# 1. DATA MODELS (FIXED: Restored ChatRequest)
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: str
    member_id: str
    message: str

# ---------------------------------------------------------
# 2. DATABASE & LOGIC SETUP (RESTORED)
# ---------------------------------------------------------
def init_db():
    """Initializes the database schema for history and token tracking."""
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
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

init_db()

# Rate Limiting & Hashing Cache
REQUEST_HISTORY_LOG = defaultdict(list)
GENERAL_RESPONSE_CACHE = {}

def is_rate_limited(session_id: str) -> bool:
    """Limits to 5 requests per 60 seconds per session."""
    current_time = time.time()
    REQUEST_HISTORY_LOG[session_id] = [t for t in REQUEST_HISTORY_LOG[session_id] if current_time - t < 60.0]
    if len(REQUEST_HISTORY_LOG[session_id]) >= 5:
        return True
    REQUEST_HISTORY_LOG[session_id].append(current_time)
    return False

def get_question_hash(question: str) -> str:
    """Creates a unique ID for a query to check the cache."""
    return hashlib.sha256(question.lower().strip().encode("utf-8")).hexdigest()

def is_eligible_for_caching(question: str) -> bool:
    """Blocks caching for queries that look like personal member data."""
    clean_q = question.lower().strip()
    restricted = ["clm", "claim", "member id", "my policy", "p10", "status of"]
    return not any(idnt in clean_q for idnt in restricted)

# ---------------------------------------------------------
# 3. API ENDPOINTS (Observability + Full Logic)
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    """Liveness probe for Kubernetes."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/chat")
async def handle_chat_endpoint(payload: ChatRequest):
    """
    Primary API Gateway. 
    Handles Rate Limiting, Caching, Agent Graph Execution, and Guardrails.
    """
    # Start the Langfuse Trace using the context manager
    with langfuse.start_as_current_observation(
        name="chat_request",
        user_id=payload.member_id,
        session_id=payload.session_id
    ) as trace:
        
        user_raw_input = payload.message
        
        # 🔒 RATE LIMIT CHECK
        if is_rate_limited(payload.session_id):
            trace.update(status_message="Rate Limited")
            return {"response": "⚠️ Too many requests. Please pause for a moment."}
        
        # 🔒 INBOUND GUARDRAIL CHECK
        if not check_input_guardrail(user_raw_input):
            trace.update(status_message="Security Block: Inbound")
            return {"response": "⚠️ Security Access Exception: Prompt not authorized."}

        # 🚀 CACHE HIT CHECK
        q_hash = get_question_hash(user_raw_input)
        cache_eligible = is_eligible_for_caching(user_raw_input)
        if cache_eligible and q_hash in GENERAL_RESPONSE_CACHE:
            cached_reply = GENERAL_RESPONSE_CACHE[q_hash]
            trace.update(output=cached_reply, metadata={"cache": "hit"})
            return {"response": cached_reply}

        # 🕸️ AGENT GRAPH EXECUTION
        with langfuse.start_as_current_observation(name="agent_graph_execution") as span:
            try:
                # Late import to keep startup fast
                from multi_agent import multi_agent_application_mesh
                
                initial_state = {
                    "user_query": user_raw_input,
                    "messages": [],
                    "next_node": "",
                    "final_output": "",
                    "session_id": payload.session_id
                }
                
                # Invoke the LangGraph State Machine
                computed_final_state = await multi_agent_application_mesh.ainvoke(initial_state)
                assistant_generated_reply = computed_final_state.get("final_output", "No response generated.")
                
                span.update(output=assistant_generated_reply)
                
            except Exception as err:
                assistant_generated_reply = f"System Error: {str(err)}"
                span.update(level="ERROR", status_message=str(err))

        # 🔒 OUTBOUND GUARDRAIL CHECK
        final_response = check_output_guardrail(assistant_generated_reply)
        
        # ⚡ CACHE WRITE
        if cache_eligible:
            GENERAL_RESPONSE_CACHE[q_hash] = final_response
        
        # 🧮 TELEMETRY (Token Counting)
        p_tokens = count_tokens(user_raw_input)
        c_tokens = count_tokens(final_response)
        
        trace.update(
            output=final_response,
            usage={"input": p_tokens, "output": c_tokens, "unit": "TOKENS"}
        )

        # 📊 PERSIST TO SQLITE
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            # Log history
            cursor.execute("INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                           (payload.session_id, "user", user_raw_input, now))
            cursor.execute("INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                           (payload.session_id, "assistant", final_response, now))
            # Log usage (Cost estimated at 0 here, calculated in dashboard)
            cursor.execute("INSERT INTO token_usage (session_id, timestamp, input_tokens, output_tokens, estimated_cost) VALUES (?, ?, ?, ?, ?)",
                           (payload.session_id, now, p_tokens, c_tokens, 0.0))
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"Database Logging Error: {db_err}")

        # PII-redacted audit log for console
        print(f"[AUDIT] {redact_pii(user_raw_input)} -> {redact_pii(final_response)}")
        
        langfuse.flush()
        return {"response": final_response}

@app.get("/history/{session_id}")
def get_session_history(session_id: str):
    """Retrieves long-term records for a specific session."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id ASC", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return {"session_id": session_id, "history": [{"role": r, "content": c} for r, c in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Start the server
    print("🚀 FastAPI Observability Gateway Live on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)