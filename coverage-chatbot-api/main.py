"""Simple script with a helper to fetch JSON from a URL."""

print("this is a simple python line of code")

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

# ---------------------------------------------------------
# FIXED: STREAMING RESPONSE ENDPOINT (POST /chat)
# ---------------------------------------------------------
@app.post("/chat")
def handle_chat_endpoint(payload: ChatRequest):
    """
    POST /chat streaming endpoint.
    Directly pipes pre-formatted SSE lines down the network wire
    while capturing the session history in memory.
    """
    start_time = time.perf_counter()
    
    if payload.session_id not in SESSION_STORE:
        SESSION_STORE[payload.session_id] = []
        
    # Step 1: Run local database index lookups
    retrieval_payload = retrieve(payload.message)
    context_block = retrieval_payload.get("context_block", "")
    
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

					# 🚀 THE FIX: Force a 30ms delay to let the frontend typewriter visibly catch up
                    time.sleep(0.03)
                    
                    # 2. Extract and accumulate token text for backend history tracking
                    if raw_sse_line.startswith("data:"):
                        try:
                            clean_json = raw_sse_line[5:].strip()
                            data_chunk = json.loads(clean_json)
                            accumulated_answer += data_chunk.get("token", "")
                        except Exception:
                            pass
            
            # 3. Save fully assembled message to history logs once the stream finishes
            SESSION_STORE[payload.session_id].append({"role": "assistant", "content": accumulated_answer})
            
            duration = time.perf_counter() - start_time
            print(f"[STREAM SUCCESS] Session: {payload.session_id} completed in {duration:.4f}s")
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            print(f"[STREAM ERROR] Pipeline crash: {str(e)}")
            yield f"data: {json.dumps({'error': 'Internal model loop execution failure'})}\n\n"

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
