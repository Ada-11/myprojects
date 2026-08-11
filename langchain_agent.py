import os
import sys
import json
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import langchainhub as hub

# FIXED: Modern v1.x core path — create_agent replaces legacy AgentExecutor
from langchain_groq import ChatGroq
from langchain.agents import create_agent

# Ensure parent directory is accessible for local module resolutions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tool_calling_chatbot import (
    check_coverage as native_check_coverage,
    get_claim_status as native_get_claim_status,
    get_plan_details as native_get_plan_details
)

# ----------------------------------------------------------------------
# 1. TOOLS REGISTRY
# ----------------------------------------------------------------------
@tool
def check_coverage(plan_id: str, procedure: str) -> str:
    """Checks if a medical procedure is covered under an insurance plan ID."""
    return native_check_coverage(plan_id=plan_id, procedure=procedure)

@tool
def get_claim_status(claim_id: str) -> str:
    """Retrieves adjudication state and payment data for a claim ID."""
    return native_get_claim_status(claim_id=claim_id)

@tool
def get_plan_details(plan_id: str) -> str:
    """Retrieves cost-sharing metrics, premium, and deductible information for a plan ID."""
    return native_get_plan_details(plan_id=plan_id)

LANGCHAIN_TOOLS_REGISTRY = [check_coverage, get_claim_status, get_plan_details]

# ----------------------------------------------------------------------
# 2. INITIALIZE NATIVE GROQ LLM COMPONENT INSTEAD OF OPENAI WRAPPERS
# ----------------------------------------------------------------------
groq_api_token = os.environ.get("GROQ_API_KEY")
if not groq_api_token:
    raise ValueError("GROQ_API_KEY environment variable is missing.")

# Directly targets the native Groq connection architecture cleanly
llm_client_engine = ChatGroq(
    groq_api_key=groq_api_token,
    model_name="llama-3.1-8b-instant",
    temperature=0.0
)

# ----------------------------------------------------------------------
# 3. CONSTRUCT MODERN REACT AGENT
# ----------------------------------------------------------------------
# Modern create_agent returns a graph-based runner ready to invoke directly
insurance_agent = create_agent(
    model=llm_client_engine,
    tools=LANGCHAIN_TOOLS_REGISTRY,
    debug=True  # ACTIVATES FULL REASONING MONOLOGUE LOGGING
)

# ----------------------------------------------------------------------
# RUN CONSOLE LOOP
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 MODERN LANGCHAIN v1.x AGENT ACTIVE")
    print("Type your insurance question and press Enter. Type 'exit' to quit.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input or user_input.lower() in ["exit", "quit", "q"]:
                break
                
            print("\n[STARTING AGENT WORKFLOW]...")
            
            # Modern v1.x execution passing a standard messages collection
            response = insurance_agent.invoke({
                "messages": [{"role": "user", "content": user_input}]
            })
            
            # Extract output string from messages response loop
            print(f"\nFinal Agent Output:\n{response['messages'][-1].content}")
            print("-" * 60)
            
        except KeyboardInterrupt:
            break
