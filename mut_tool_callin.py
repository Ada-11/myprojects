import os
import sys
import json
import sqlite3
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ValidationError
from groq import Groq
import tiktoken
from dotenv import load_dotenv

# --- INITIALIZE ---
load_dotenv()
from langfuse import Langfuse
langfuse = Langfuse()

DB_PATH_GLOBAL = "coverage-chatbot-api/coverage.db"

# ---------------------------------------------------------
# 1. PYDANTIC OUTPUT DATA SCHEMAS (RESTORED)
# ---------------------------------------------------------
class CoverageValidationModel(BaseModel):
    plan_id: str = Field(..., min_length=2)
    procedure: str = Field(..., min_length=3)
    is_covered: bool
    limitations: str
    pre_authorization_required: bool

class ClaimStatusValidationModel(BaseModel):
    claim_id: str = Field(..., min_length=4)
    status: str = Field(..., pattern="^(paid|denied|pending_review)$")
    submitted_amount: float = Field(..., ge=0.0)
    allowed_amount: Optional[float] = Field(None, ge=0.0)
    member_responsibility: Optional[float] = Field(None, ge=0.0)
    insurance_paid: Optional[float] = Field(None, ge=0.0)
    denial_reason: Optional[str] = None

# ---------------------------------------------------------
# 2. MOCK DATASETS (RESTORED)
# ---------------------------------------------------------
MOCK_COVERAGE = [
    {"plan_id": "P101", "procedure": "physical therapy", "is_covered": True, "limitations": "20 visits/year", "pre_authorization_required": False},
    {"plan_id": "P102", "procedure": "acupuncture", "is_covered": False, "limitations": "Excluded", "pre_authorization_required": False}
]

MOCK_CLAIMS = [
    {"claim_id": "CLM9901", "status": "paid", "submitted_amount": 450.00, "allowed_amount": 350.00, "member_responsibility": 35.00, "insurance_paid": 315.00, "denial_reason": None}
]

# ---------------------------------------------------------
# 3. REALIZATION FUNCTIONS (With Manual Tracing)
# ---------------------------------------------------------
def check_coverage(plan_id: str, procedure: str) -> str:
    with langfuse.start_as_current_observation(name="tool_check_coverage", input={"plan": plan_id}) as span:
        p_clean = procedure.strip().lower()
        raw_match = next((i for i in MOCK_COVERAGE if i["plan_id"].upper() == plan_id.strip().upper() and i["procedure"] == p_clean), None)
        if not raw_match:
            raw_match = {"plan_id": plan_id, "procedure": procedure, "is_covered": False, "limitations": "No record found.", "pre_authorization_required": False}
        res = CoverageValidationModel(**raw_match).model_dump_json()
        span.update(output=res)
        return res

def get_claim_status(claim_id: str) -> str:
    with langfuse.start_as_current_observation(name="tool_get_claim_status", input={"claim_id": claim_id}) as span:
        raw_match = next((i for i in MOCK_CLAIMS if i["claim_id"].upper() == claim_id.strip().upper()), None)
        if not raw_match: return json.dumps({"error": "Claim not found."})
        res = ClaimStatusValidationModel(**raw_match).model_dump_json()
        span.update(output=res)
        return res

# ---------------------------------------------------------
# 4. MEMORY COMPRESSION DAEMON (RESTORED)
# ---------------------------------------------------------
def prune_and_summarize_session_history(session_id: str, db_path: str, groq_client: Groq):
    with langfuse.start_as_current_observation(name="memory_compression") as span:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id ASC", (session_id,))
            rows = cursor.fetchall()
            if len(rows) < 15: 
                conn.close()
                return
            
            digest = "\n".join([f"{r.upper()}: {c}" for r, c in rows[:8]])
            summary_prompt = f"Summarize concisely as a system log paragraph:\n{digest}"
            response = groq_client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role": "user", "content": summary_prompt}])
            summary = response.choices[0].message.content
            
            # Simplified cleanup for this script
            cursor.execute("INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                           (session_id, "system", f"[AUTO-SUMMARY]: {summary}", datetime.now(timezone.utc).isoformat()))
            conn.commit(); conn.close()
            span.update(output="Compressed older turns successfully.")
        except Exception as e:
            span.update(level="ERROR", status_message=str(e))

# ---------------------------------------------------------
# 5. AGENT RUNTIME (GPT OSS 20B)
# ---------------------------------------------------------
def run_agent_loop(user_query: str, external_context: str = "", stream: bool = True, session_id: str = "DEFAULT-SESS"):
    ACTIVE_MODEL = "openai/gpt-oss-20b"
    
    with langfuse.start_as_current_observation(name="llm_agent_run", input=user_query, metadata={"session_id": session_id}) as generation:
        api_key = os.environ.get("GROQ_API_KEY")
        client = Groq(api_key=api_key)
        
        # Trigger Memory Management
        prune_and_summarize_session_history(session_id, DB_PATH_GLOBAL, client)

        messages = [
            {"role": "system", "content": "You are a professional Health Insurance Navigator. Use provided data. No medical advice."},
            {"role": "user", "content": user_query}
        ]

        try:
            response = client.chat.completions.create(model=ACTIVE_MODEL, messages=messages, temperature=0.0)
            final_text = response.choices[0].message.content
            
            generation.update(
                output=final_text, model=ACTIVE_MODEL,
                usage={"input": response.usage.prompt_tokens, "output": response.usage.completion_tokens}
            )

            if stream:
                # This is the format the frontend UI expects
                yield f"data: {json.dumps({'token': final_text})}\n\n"
            else:
                return final_text

        except Exception as api_err:
            generation.update(level="ERROR", status_message=str(api_err))
            yield f"data: {json.dumps({'error': str(api_err)})}\n\n"
    langfuse.flush()

# ---------------------------------------------------------
# LOCAL RUNNER (RESTORED + CLEAN OUTPUT FIX)
# ---------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 RUNNING FULL LOGIC AGENT (Clean Output Mode)")
    print("=" * 60)
    
    for sse_line in run_agent_loop("What is my deductible?", session_id="TEST-999"):
        if sse_line.startswith("data:"):
            # This parses the 'messy' JSON into clean terminal text
            raw_data = sse_line.replace("data: ", "").strip()
            try:
                json_data = json.loads(raw_data)
                if "token" in json_data:
                    print(json_data["token"], end="", flush=True)
                elif "error" in json_data:
                    print(f"\n❌ Error: {json_data['error']}")
            except:
                pass
    print("\n" + "-"*60)