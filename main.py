"""
Main FastAPI Gateway for Agentic Health Insurance Chatbot.
Handles SSE Streaming, Rate Limiting, SHA-256 Caching, 
Observability (Langfuse v4), and SQLite Persistence.
"""

import sys
import os
import time
import json
import sqlite3
import hashlib
import urllib.request
import urllib.error
import asyncio
from datetime import datetime, timezone
from typing import Any, List, Optional, Literal, TypedDict
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# --- INITIALIZE ENVIRONMENT & OBSERVABILITY ---
load_dotenv()
from langfuse import Langfuse
# Initialize the manual client for SDK v4 compatibility
# This ensures stability on Mac and within Kubernetes containers
langfuse = Langfuse()

# --- PROJECT MODULE IMPORTS ---
# These must exist in your root directory or PYTHONPATH
from retrieval_engine import retrieve
from redact_pii import redact_pii
from guardrails_config import check_input_guardrail, check_output_guardrail
from token_utils import count_tokens

app = FastAPI(
    title="Insurance Agent API",
    description="Production-grade API for health insurance policy navigation."
)

# ---------------------------------------------------------
# 1. DATABASE INITIALIZATION: SQLITE STORAGE ENGINE
# ---------------------------------------------------------
# Configuration: Absolute path for Kubernetes volume mounts
DB_PATH = "/app/coverage-chatbot-api/coverage.db"

# Fallback for local Mac development if the /app directory does not exist
if not os.path.exists("/app"):
    DB_PATH = "coverage-chatbot-api/coverage.db"

def init_db():
    """
    Initializes the database schema for structural conversation history 
    and detailed token/cost usage tracking.
    """
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for long-term chat history and session persistence
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    
    # Table for observability analytics and financial auditing
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

# Provision database on server initialization
init_db()

# ---------------------------------------------------------
# 2. REQUEST MODELS, RATE LIMITING & CACHING
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: str
    member_id: str
    message: str

# Global rate limiting thresholds (Max 5 requests per 60 seconds per session)
RATE_LIMIT_CEILING = 5
RATE_LIMIT_WINDOW = 60.0
REQUEST_HISTORY_LOG = defaultdict(list)

def is_rate_limited(session_id: str) -> bool:
    """Checks sliding window request counts for the current session."""
    current_time = time.time()
    # Purge old records outside the active 60s window frame
    REQUEST_HISTORY_LOG[session_id] = [t for t in REQUEST_HISTORY_LOG[session_id] if current_time - t < RATE_LIMIT_WINDOW]
    
    if len(REQUEST_HISTORY_LOG[session_id]) >= RATE_LIMIT_CEILING:
        return True
        
    REQUEST_HISTORY_LOG[session_id].append(current_time)
    return False

# Global In-Memory Exact Match Data Cache
GENERAL_RESPONSE_CACHE = {}

def get_question_hash(question: str) -> str:
    """Normalizes the string and computes a secure SHA-256 hex string hash."""
    normalized = question.lower().strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def is_eligible_for_caching(question: str) -> bool:
    """
    SECURITY FILTER: Determines if a query can be safely cached.
    Explicitly blocks member-specific questions containing claim or tracking identifiers.
    """
    clean_q = question.lower().strip()
    restricted_identifiers = [
        "clm", "claim", "member id", "my policy", "my balance", 
        "status of", "p10", "p11", "em9", "john doe"
    ]
    
    for identifier in restricted_identifiers:
        if identifier in clean_q:
            return False
            
    return True

def fetch_json(url: str, timeout: int = 10) -> Any:
    """Standard helper to fetch JSON from external URLs (e.g., for RAG context)."""
    req = urllib.request.Request(url, headers={"User-Agent": "python-urllib/3"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset(failobj="utf-8")
            data = resp.read().decode(charset)
            return json.loads(data)
    except Exception as e:
        print(f"[FETCH ERROR] {e}")
        return None

# ---------------------------------------------------------
# 3. API ENDPOINTS (Streaming + Observability)
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    """Standard RFC-compliant health check for Kubernetes liveness/readiness probes."""
    return {
        "status": "healthy", 
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": os.path.exists(DB_PATH)
    }

@app.post("/chat")
async def handle_chat_endpoint(payload: ChatRequest):
    """
    Main Chat Interface. 
    Returns a StreamingResponse (SSE) compatible with the Streamlit UI.
    Updated with Structured Bridge to send Card Data.
    """
    
    async def event_generator():
        # Start the manual Langfuse Trace for v4 compatibility
        with langfuse.start_as_current_observation(
            name="chat_request",
            metadata={
                "user_id": payload.member_id,
                "session_id": payload.session_id,
                "deployment": "k8s-minikube",
                "cache_enabled": True
            }
        ) as trace:
            
            user_raw_input = payload.message
            
            # 🔒 RATE LIMIT GATEWAY
            if is_rate_limited(payload.session_id):
                trace.update(status_message="Rate Limit Triggered")
                yield f"data: {json.dumps({'error': 'Rate limit exceeded.'})}\n\n"
                return
            
            # 🔒 SECURITY BLOCK: Inbound
            if not check_input_guardrail(user_raw_input):
                trace.update(status_message="Inbound Block")
                yield f"data: {json.dumps({'error': 'Security Access Exception.'})}\n\n"
                return

            # 🚀 CACHE READ HIT
            q_hash = get_question_hash(user_raw_input)
            cache_eligible = is_eligible_for_caching(user_raw_input)
            
            if cache_eligible and q_hash in GENERAL_RESPONSE_CACHE:
                cached_data = GENERAL_RESPONSE_CACHE[q_hash]
                trace.update(output=cached_data['token'], metadata={"cache": "hit"})
                yield f"data: {json.dumps(cached_data)}\n\n"
                return

            # 🕸️ AGENT GRAPH EXECUTION SPAN
            with langfuse.start_as_current_observation(name="agent_graph_execution") as span:
                try:
                    from multi_agent import multi_agent_application_mesh
                    
                    initial_state = {
                        "user_query": user_raw_input,
                        "session_id": payload.session_id,
                        "messages": [],
                        "next_node": "",
                        "final_output": "",
                        "card_type": None,
                        "card_payload": None
                    }
                    
                    computed_final_state = await multi_agent_application_mesh.ainvoke(initial_state)
                    
                    assistant_generated_reply = computed_final_state.get("final_output", "No response.")
                    detected_card_type = computed_final_state.get("card_type")
                    detected_card_payload = computed_final_state.get("card_payload")
                    
                    span.update(output=assistant_generated_reply)
                    
                except Exception as err:
                    assistant_generated_reply = f"System failure: {str(err)}"
                    detected_card_type, detected_card_payload = None, None
                    span.update(level="ERROR", status_message=str(err))

            # 🔒 SECURITY BLOCK: Outbound
            final_sanitized_ui_response = check_output_guardrail(assistant_generated_reply)
            
            # 🧮 TOKEN TELEMETRY
            prompt_token_count = count_tokens(user_raw_input)
            completion_token_count = count_tokens(final_sanitized_ui_response)
            trace.update(
                output=final_sanitized_ui_response,
                usage={"input": prompt_token_count, "output": completion_token_count}
            )

            # 📊 PERSISTENT TRANSACTION LOGGING
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                
                cursor.execute("INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                               (payload.session_id, "user", user_raw_input, now_ts))
                cursor.execute("INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                               (payload.session_id, "assistant", final_sanitized_ui_response, now_ts))
                
                estimated_cost = (prompt_token_count * (0.05/1000000)) + (completion_token_count * (0.08/1000000))
                cursor.execute("""
                    INSERT INTO token_usage (session_id, timestamp, input_tokens, output_tokens, estimated_cost)
                    VALUES (?, ?, ?, ?, ?)
                """, (payload.session_id, now_ts, prompt_token_count, completion_token_count, estimated_cost))
                
                conn.commit()
                conn.close()
            except Exception as db_err:
                print(f"⚠️ [DATABASE ERROR] {db_err}")

            # 📺 PACKAGE PAYLOAD FOR STREAM & CACHE
            response_payload = {
                'token': final_sanitized_ui_response,
                'card_type': detected_card_type,
                'card_payload': detected_card_payload
            }

            if cache_eligible:
                GENERAL_RESPONSE_CACHE[q_hash] = response_payload

            langfuse.flush()
            yield f"data: {json.dumps(response_payload)}\n\n"
            print(f"[AUDIT] {redact_pii(user_raw_input)} -> {redact_pii(final_sanitized_ui_response)} [UI: {detected_card_type}]")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/history/{session_id}")
def get_session_history(session_id: str):
    """Retrieves records out of the SQLite conversations table for UI restoration."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
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


if __name__ == "__main__":
    import uvicorn
    print("🚀 PRODUCTION OBSERVABILITY GATEWAY STARTING ON http://0.0.0.0:8000")
    print(f"📍 TARGET DATABASE: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)