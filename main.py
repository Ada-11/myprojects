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

from token_utils import count_tokens
from collections import defaultdict
import time
import hashlib


app = FastAPI()

@app.get("/health")

def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

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


import time
from collections import defaultdict

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
    
    # Identify high-risk personal search patterns
    restricted_identifiers = [
        "clm", "claim", "member id", "my policy", "my balance", 
        "status of", "p10", "p11", "em9", "john doe"
    ]
    
    for identifier in restricted_identifiers:
        if identifier in clean_q:
            print(f"🔒 [CACHE BYPASS] Query contains member-specific identifier '{identifier}'. Disabling cache.")
            return False
            
    return True

# ---------------------------------------------------------
# 2. CARDS + STREAMING PIPELINE ENDPOINT (POST /chat)
# ---------------------------------------------------------
@app.post("/chat")
async def handle_chat_endpoint(payload: ChatRequest):
    """
    POST /chat endpoint. Hardened against crashes, protected by security guardrails,
    rate-limited per session, optimized with tiktoken tracking, and accelerated with a
    privacy-aware exact-match general query cache.
    """
    start_time = time.perf_counter()
    user_raw_input = payload.message
    
    # 🔒 RATE LIMIT GATEWAY: Intercept spam attempts at the absolute front door
    if is_rate_limited(payload.session_id):
        print(f"⚠️ [RATE LIMIT TRIGGER] Denied request stream block for session: {payload.session_id}")
        return {
            "response": "⚠️ Too many requests. You have exceeded our security standard of 5 requests per minute. Please pause and try your question again in a few moments."
        }
    
    # 🧮 STEP 1: CALCULATE THE RAW INBOUND PROMPT TOKEN SIZE IMMEDIATELY
    prompt_token_count = count_tokens(user_raw_input)
    
    # 🔒 SAFE INTERCEPTION GATE: Returns a clean string if input fails validation
    if not check_input_guardrail(user_raw_input):
        print("🛡️ [SECURITY INTERCEPT] Inbound block executed. Preventing loop run.")
        print(f"[METRIC LOG] Intercepted Prompt Token Size: {prompt_token_count}")
        return {"response": "⚠️ Security Access Exception: Malicious, off-topic, or unapproved prompt signature detected."}

    # 🚀 CACHE READ HIT CLOSURE: Evaluate exact-match general coverage shortcuts
    q_hash = get_question_hash(user_raw_input)
    cache_eligible = is_eligible_for_caching(user_raw_input)
    
    if cache_eligible and q_hash in GENERAL_RESPONSE_CACHE:
        cached_reply = GENERAL_RESPONSE_CACHE[q_hash]
        print(f"⚡ [CACHE HIT] Serving optimized, zero-token response for: '{user_raw_input}'")
        
        # Log zero tokens for the outbound trace logging records
        print(f"[AUDIT TRACE LOG] Ingress: {redact_pii(user_raw_input)} | Egress (CACHED): {redact_pii(cached_reply)}")
        return {"response": cached_reply}
    
    # Run database index lookups using raw string variables (Cache Miss Path)
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
    # 🕸️ CORE COGNITION GENERATION LOOP BLOCK: CONNECT THE REAL AGENT GRAPH
    # ----------------------------------------------------------------------
    try:
        # Import your actual live agent app instance from your multi-agent module
        from multi_agent import multi_agent_application_mesh
        
        # Package your active request inputs straight into your formal state dict
        initial_graph_state = {
            "user_query": user_raw_input,
            "messages": [],
            "next_node": "",
            "final_output": "",
            "session_id": payload.session_id
        }
        
        print(f"🕸️ [LIVE GRAPH INVOKE] Running multi-agent application mesh flow dynamically...")
        
        # Invoke your existing agent mesh over async threads natively
        computed_final_state = await multi_agent_application_mesh.ainvoke(initial_graph_state)
        
        # Extract the real ground-truth generated text value into your output channel
        assistant_generated_reply = computed_final_state.get("final_output", "Error: No final output computed by graph.")
        
    except Exception as err:
        print(f"⚠️ [GRAPH ERROR] Failed running live multi-agent execution pipeline: {str(err)}")
        assistant_generated_reply = f"System lookup failure: Multi-agent compilation interrupted. Error: {str(err)}"
        
    # 🔒 SECURITY STEP 2: RUN THE GENERATION THROUGH OUTBOUND GUARDRAILS
    final_sanitized_ui_response = check_output_guardrail(assistant_generated_reply)
    
    # ⚡ CACHE WRITE PATH: Store the response safely if the question is generic coverage
    if cache_eligible:
        GENERAL_RESPONSE_CACHE[q_hash] = final_sanitized_ui_response
        print(f"💾 [CACHE WRITE] Saved general coverage response hash key entry down to memory index.")
    
    # 🧮 STEP 3: CALCULATE THE SAFELY SANITIZED OUTBOUND COMPLETION TOKEN SIZE
    completion_token_count = count_tokens(final_sanitized_ui_response)
    
    # 📊 STEP 4: LOG THE COMBINED TRANSACTION PERFORMANCE AND PRICING METRICS
    total_turn_tokens = prompt_token_count + completion_token_count
    input_rate_per_token = 0.05 / 1_000_000
    output_rate_per_token = 0.08 / 1_000_000
    estimated_cost = (prompt_token_count * input_rate_per_token) + (completion_token_count * output_rate_per_token)
    current_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # PERSISTENT METRIC LOGGING TRANSACTION BLOCK
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO token_usage (session_id, timestamp, input_tokens, output_tokens, estimated_cost)
            VALUES (?, ?, ?, ?, ?)
        """, (payload.session_id, current_timestamp, prompt_token_count, completion_token_count, estimated_cost))
        conn.commit()
        conn.close()
    except Exception as db_metric_err:
        print(f"⚠️ [METRIC LOG ERROR] Failed to record token analytics to SQLite: {str(db_metric_err)}")
    
    print(f"\n" + "="*15 + " 📊 REAL-TIME TURN TOKEN METRICS " + "="*15)
    print(f"▶ Inbound Prompt footprint:      {prompt_token_count} tokens")
    print(f"▶ Outbound Completion footprint:  {completion_token_count} tokens")
    print(f"▶ Total Single-Turn Footprint:   {total_turn_tokens} tokens")
    print(f"▶ Financial Transaction Expense: ${estimated_cost:.8f}")
    print("="*60 + "\n")
    
    # Anonymize analytical text fields for secure trace log storage dumps (Scenario 1)
    safe_log_prompt = redact_pii(user_raw_input)
    safe_log_response = redact_pii(final_sanitized_ui_response)
    print(f"[AUDIT TRACE LOG] Ingress: {safe_log_prompt} | Egress: {safe_log_response}")
    
    return {"response": final_sanitized_ui_response}
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
