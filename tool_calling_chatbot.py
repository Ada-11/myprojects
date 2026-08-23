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

load_dotenv()
from langfuse import Langfuse
langfuse = Langfuse()

DB_PATH_GLOBAL = "/app/coverage-chatbot-api/coverage.db"
if not os.path.exists(DB_PATH_GLOBAL):
    DB_PATH_GLOBAL = "coverage-chatbot-api/coverage.db"

ACTIVE_MODEL = "openai/gpt-oss-20b"

# ---------------------------------------------------------
# 1. MODELS & DATA (PRODUCED BY THE DB)
# ---------------------------------------------------------
class CoverageValidationModel(BaseModel):
    plan_id: str; procedure: str; is_covered: bool; limitations: str; pre_authorization_required: bool

class ClaimStatusValidationModel(BaseModel):
    claim_id: str; status: str; submitted_amount: float; allowed_amount: Optional[float]; insurance_paid: Optional[float]

# EXTENDED MOCK DATA to handle more keywords
MOCK_COVERAGE = [
    {"plan_id": "P101", "procedure": "deductible", "is_covered": True, "limitations": "$2,000 Annual Individual.", "pre_authorization_required": False},
    {"plan_id": "P102", "procedure": "deductible", "is_covered": True, "limitations": "$1,500 Annual Individual.", "pre_authorization_required": False},
    {"plan_id": "P101", "procedure": "copay", "is_covered": True, "limitations": "10% Coinsurance.", "pre_authorization_required": False},
    {"plan_id": "P102", "procedure": "copay", "is_covered": True, "limitations": "20% Coinsurance.", "pre_authorization_required": False},
    {"plan_id": "P101", "procedure": "cosmetic procedure", "is_covered": False, "limitations": "Excluded under Gold policy terms.", "pre_authorization_required": False},
    {"plan_id": "P101", "procedure": "physical therapy", "is_covered": True, "limitations": "20 visits/year.", "pre_authorization_required": False}
]

# ---------------------------------------------------------
# 2. RUNTIME
# ---------------------------------------------------------
def run_agent_loop(user_query: str, external_context: str = "", stream: bool = True, session_id: str = "DEFAULT-SESS"):
    with langfuse.start_as_current_observation(name="llm_agent_run", input=user_query, metadata={"session_id": session_id}) as generation:
        api_key = os.environ.get("GROQ_API_KEY")
        client = Groq(api_key=api_key)
        
        messages = [
            {"role": "system", "content": "You are a professional Health Insurance Navigator. No medical advice. Talk text only."},
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
                yield f"data: {json.dumps({'token': final_text})}\n\n"
            else:
                return final_text

        except Exception as api_err:
            generation.update(level="ERROR", status_message=str(api_err))
            yield f"data: {json.dumps({'error': str(api_err)})}\n\n"
    langfuse.flush()

if __name__ == "__main__":
    for sse_line in run_agent_loop("Is physical therapy covered?", session_id="CLI-STABLE"):
        print(sse_line.strip())