
"""Simple script with a helper to fetch JSON from a URL."""

import time
from typing import Any
import json
import urllib.request
import urllib.error
import sys
import os
# Dynamically append the parent directory to Python's file tracking path matrix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# MINIMAL REQUIREMENT: Import web server, parameter contracts, and exception objects
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import your core pipeline components from your project files
from retrieval_engine import retrieve
from retrieval_engine import retrieve
# FIXED: Change import target string to match your verified file contents
from tool_calling_chatbot import run_agent_loop

app = FastAPI()

SESSION_STORE = {}

class ChatRequest(BaseModel):
    session_id: str
    member_id: str
    message: str

@app.post("/chat")
def handle_chat_endpoint(payload: ChatRequest):
    start_time = time.perf_counter()
    
    if payload.session_id not in SESSION_STORE:
        SESSION_STORE[payload.session_id] = []
        
    retrieval_payload = retrieve(payload.message)
    context_block = retrieval_payload.get("context_block", "")
    
    SESSION_STORE[payload.session_id].append({"role": "user", "content": payload.message})
    
    try:
        # FIXED: Call run_agent_loop to process and print the chat transaction pass cleanly
        bot_final_answer = run_agent_loop(payload.message)
    except Exception as e:
        duration = time.perf_counter() - start_time
        print(f"[BACKEND ERROR LOG] Execution failed after {duration:.4f}s. Exception Details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal RAG server engine exception. The LLM connection pipeline failed to process the request.")
        
        # REQUIRED: Raise a clean, graceful HTTP 500 error status code block back to the user
        raise HTTPException(
            status_code=500,
            detail="Internal RAG server engine exception. The LLM connection pipeline failed to process the request."
        )
    
    # Append the model's generated answer into the conversation state on success
    SESSION_STORE[payload.session_id].append({"role": "assistant", "content": bot_final_answer})
    
    # REQUIRED: Print successful request-timing telemetry logs directly to server terminal window
    duration = time.perf_counter() - start_time
    print(f"[BACKEND SUCCESS LOG] Session: {payload.session_id} | Execution Time Duration: {duration:.4f}s")
    
    return {
        "session_id": payload.session_id,
        "member_id": payload.member_id,
        "agent_response": bot_final_answer
    }

# GET /history/{session_id} route
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
