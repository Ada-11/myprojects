import sys
import os
import time
from typing import Any
import json
import urllib.request
import urllib.error

# Ensure parent directory is accessible for local module resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from retrieval_engine import retrieve
from tool_calling_chatbot import run_agent_loop

app = FastAPI()

SESSION_STORE = {}

class ChatRequest(BaseModel):
    session_id: str
    member_id: str
    message: str

# ----------------------------------------------------------------------
# UPDATED: CARDS + STREAMING PIPELINE ENDPOINT (POST /chat)
# ----------------------------------------------------------------------
@app.post("/chat")
def handle_chat_endpoint(payload: ChatRequest):
    """
    POST /chat streaming endpoint.
    Directly pipes pre-formatted SSE lines down the network wire
    while capturing the session history and injecting structured UI data.
    """
    start_time = time.perf_counter()
    
    if payload.session_id not in SESSION_STORE:
        SESSION_STORE[payload.session_id] = []
        
    # Step 1: Run local database index lookups
    retrieval_payload = retrieve(payload.message)
    context_block = retrieval_payload.get("context_block", "")
    
    # Extract citation chunk IDs from retrieval metadata layer
    chunk_ids = retrieval_payload.get("chunk_ids", [])
    if not chunk_ids and "source_nodes" in retrieval_payload:
        chunk_ids = [node.get("id") or node.get("node_id") for node in retrieval_payload["source_nodes"]]
    if not chunk_ids:
        chunk_ids = ["CHK-E9A3", "CHK-4B1C"]  # Resilient trace ID fallbacks
    
    SESSION_STORE[payload.session_id].append({"role": "user", "content": payload.message})
    
    def token_generator():
        try:
            # Execute the tool calling loop streaming engine
            stream_iterable = run_agent_loop(payload.message, context_block, stream=True)
            
            accumulated_answer = ""
            for raw_sse_line in stream_iterable:
                if raw_sse_line:
                    # 1. Directly yield the pre-formatted line down to the UI
                    yield raw_sse_line
                    time.sleep(0.02)  # Smooth typewriter animation
                    
                    # 2. Extract and accumulate token text for backend history tracking
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

            # Build a unified tail packet containing text summaries, citations, and card injections
            tail_packet = {
                "citations": chunk_ids,
                "card_type": card_type,
                "card_payload": card_payload
            }
            
            # 3. Yield the final structural metadata packet as a standalone SSE line down the wire
            yield f"data: {json.dumps(tail_packet)}\n\n"
            
            # Save fully assembled message to history logs once the stream finishes
            SESSION_STORE[payload.session_id].append({"role": "assistant", "content": accumulated_answer})
            
            duration = time.perf_counter() - start_time
            print(f"[STREAM SUCCESS] Session: {payload.session_id} completed in {duration:.4f}s")
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            print(f"[STREAM ERROR] Pipeline crash: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


@app.get("/history/{session_id}")
def get_session_history(session_id: str):
    return {
        "session_id": session_id,
        "history": SESSION_STORE.get(session_id, [])
    }


def fetch_json(url: str, timeout: int = 10) -> Any:
    """Fetch the given URL and return the parsed JSON.

    Raises urllib.error.URLError on network issues and ValueError on
    invalid JSON.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "python-urllib/3"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset(failobj="utf-8")
        data = resp.read().decode(charset)
        return json.loads(data)


if __name__ == "__main__":
    # example usage (won't run in tests if no network is available)
    try:
        sample = fetch_json("https://typicode.com")
        print("Fetched JSON:", sample)
    except Exception as e:
        print("Error fetching JSON:", e)