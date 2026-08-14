import os
import sys
import json
import sqlite3
import asyncio
from typing import Literal, TypedDict, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

# Import low-level MCP asynchronous transport clients
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Ensure parent directory is accessible for local module resolutions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tool_calling_chatbot import (
    check_coverage as native_check_coverage,
    get_claim_status as native_get_claim_status
)

# Define absolute database tracking path matching your Day 20 specifications
DB_PATH = "/Users/ada/myprojects/my-first-app/coverage-chatbot-api/coverage.db"

# ----------------------------------------------------------------------
# 1. STATE MANAGEMENT CONTRACT
# ----------------------------------------------------------------------
class AgentGraphState(TypedDict):
    """Unified state tracking matrix holding message bundles and tracking tags."""
    messages: List[dict]
    next_node: str
    user_query: str
    final_output: str
    session_id: str  # Injected persistent tracking descriptor key

class RouteDecision(BaseModel):
    """Structured Pydantic contract enforcing deterministic routing paths."""
    intent_classification: Literal["coverage", "claims", "enrollment"]
    next_action_node: Literal["CoverageSpecialist", "ClaimsSpecialist", "EnrollmentHandler"]
    routing_reasoning: str

# ----------------------------------------------------------------------
# 2. SQLITE HISTORY EXTRACTION & PLAN MEMORY SINK UTILITY
# ----------------------------------------------------------------------
def load_session_history_and_plan(session_id: str) -> tuple:
    """
    Connects to the Day 20 SQLite ledger to load the sliding window history 
    and identify any previously specified plan selections.
    """
    historical_turns = []
    remembered_plan_id = "Not Specified Yet"
    
    if not os.path.exists(DB_PATH):
        return [], remembered_plan_id
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        for role, content in rows:
            historical_turns.append({"role": role, "content": content})
            content_upper = content.upper()
            if "P101" in content_upper or "GOLD PPO" in content_upper:
                remembered_plan_id = "P101 (Gold PPO)"
            elif "P102" in content_upper or "SILVER HMO" in content_upper:
                remembered_plan_id = "P102 (Silver HMO)"
            elif "P103" in content_upper or "BRONZE HMO" in content_upper:
                remembered_plan_id = "P103 (Bronze HMO)"
    except Exception as e:
        print(f"[WARN] Failed fetching SQLite history frame: {str(e)}", file=sys.stderr)
        
    # Isolate rolling last 10 messages (sliding window) to save context tokens
    sliding_window = historical_turns[-10:] if len(historical_turns) > 10 else historical_turns
    return sliding_window, remembered_plan_id

# ----------------------------------------------------------------------
# 3. CHAOS-DEFENDED UNIVERSAL MCP TOOL RUNNER CLIENT LAYER
# ----------------------------------------------------------------------
async def call_mcp_tool(tool_name: str, tool_args: dict) -> str:
    """
    Asynchronous MCP client with a 10-second timeout, 1-pass retry logic,
    and a graceful, non-crashing member support deflection fallback wrapper.
    """
    server_params = StdioServerParameters(
        command="python3",
        args=[os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")]
    )
    
    # Define our strict production chaos parameters
    MAX_ATTEMPTS = 2  # Primary attempt + exactly 1 retry
    TIMEOUT_SECONDS = 10.0
    CANNED_FALLBACK_RESPONSE = (
        "⚠️ I'm having trouble accessing that policy database right now. "
        "Please contact member support directly at 1-800-555-0199 for real-time assistance, "
        "or try again in a few moments."
    )
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(f"📡 [MCP CLIENT WIRE] Execution Attempt #{attempt} for tool '{tool_name}'...")
            
            # Enforce an explicit execution timeframe cap boundary
            async with asyncio.timeout(TIMEOUT_SECONDS):
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        # Negotiate JSON-RPC parameters
                        await session.initialize()
                        
                        # Fire request down the transport channel
                        result = await session.call_tool(tool_name, arguments=tool_args)
                        
                        if result and result.content and len(result.content) > 0:
                            # Return the successful payload instantly, breaking the retry loop
                            return result.content[0].text
                            
                        raise ValueError("Empty or malformed payload returned from protocol server.")
                        
        except asyncio.TimeoutError:
            print(f"⏳ [TIMEOUT BREACH] Attempt #{attempt} exceeded the {TIMEOUT_SECONDS}s window threshold limit.", file=sys.stderr)
        except Exception as e:
            print(f"💥 [TOOL RUNTIME CRASH] Attempt #{attempt} encountered an exception error: {str(e)}", file=sys.stderr)
            
        # Give the sub-process engine a micro-pause to settle before firing a retry pass
        if attempt < MAX_ATTEMPTS:
            await asyncio.sleep(0.5)

    # 🛑 OVERFLOW GATE: If both attempts are exhausted, intercept the failure gracefully
    print("🛡️ [CHAOS DEFENSE ACTIVATED] Tool chain exhausted. Deflecting to user-friendly canned support message.")
    return CANNED_FALLBACK_RESPONSE

# ----------------------------------------------------------------------
# 4. MEMORY-GROUNDED AGENT GRAPH NODES
# ----------------------------------------------------------------------
async def router_node(state: AgentGraphState) -> dict:
    """Supervisor Router: Classifies user intent and injects session parameters."""
    print("\n" + "="*15 + " 🔀 NODE 1: SUPERVISOR ROUTER " + "="*15)
    groq_api_token = os.environ.get("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_token, model_name="llama-3.1-8b-instant", temperature=0.0)
    structured_router = llm.with_structured_output(RouteDecision)
    
    # Load SQLite history and sticky plan metrics into the active prompt layer
    history, plan_id = load_session_history_and_plan(state.get("session_id", "DEFAULT-SESS"))
    print(f"[PLAN MEMORY] Found sticky plan state for session: **{plan_id}**")
    
    system_prompt = (
        "Analyze the query and pick the single best specialist agent node.\n"
        f"⚙️ ACTIVE MEMBER PERSISTENT PLAN VALUE: {plan_id}\n\n"
        "MAPPING RULES:\n"
        "1. Policy rules, inclusions, visit limits -> route to 'CoverageSpecialist'.\n"
        "2. Claims state, paid amounts, denials, billing -> route to 'ClaimsSpecialist'.\n"
        "3. Premium costs, HR setup, enrollments -> route to 'EnrollmentHandler'."
    )
    user_query_text = state.get("user_query", "")
    routing_result: RouteDecision = structured_router.invoke(f"{system_prompt}\n\nQuery: {user_query_text}")
    
    print(f"▶ Target Specialist Selected: `{routing_result.next_action_node}`")
    return {"next_node": routing_result.next_action_node}

async def coverage_specialist_node(state: AgentGraphState) -> dict:
    """Agent 2: Coverage Specialist utilizing memory and live MCP tools."""
    print("\n" + "="*15 + " 🛡️ NODE 2: POLICY COVERAGE EXPERT " + "="*15)
    groq_api_token = os.environ.get("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_token, model_name="llama-3.1-8b-instant", temperature=0.0)
    user_query_text = state.get("user_query", "")
    
    # Read history to find plan_id if omitted in the current user prompt turn
    history, remembered_plan_id = load_session_history_and_plan(state.get("session_id", "DEFAULT-SESS"))
    
    plan_id = "P101" # Default fallback
    if "p102" in remembered_plan_id.lower() or "p102" in user_query_text.lower(): plan_id = "P102"
    elif "p103" in remembered_plan_id.lower() or "p103" in user_query_text.lower(): plan_id = "P103"
    elif "p101" in remembered_plan_id.lower() or "p101" in user_query_text.lower(): plan_id = "P101"
    
    procedure = "physical therapy"
    if "acupuncture" in user_query_text.lower(): procedure = "acupuncture"
    elif "mri" in user_query_text.lower(): procedure = "mri scan"
    
    print(f"[CONTEXT EXECUTION] Evaluated Plan Context: {plan_id} (Resolved from memory storage layer)")
    mcp_response_json = await call_mcp_tool("check_coverage", {"plan_id": plan_id, "procedure": procedure})
    
    instruction_prompt = (
        "Context: You are an elite Health Insurance Policy Coverage Specialist.\n"
        f"Remembered Session Plan ID context: {plan_id}\n"
        "Instruction: Summarize procedure coverage rules accurately from the tool data.\n"
        "Conclude with this exact disclaimer: 'This is a structural coverage determination based on exact policy terms. This is not medical advice.'"
    )
    
    # Construct complete prompt compiling sliding conversation turns
    prompt_messages = [{"role": "system", "content": instruction_prompt}]
    for turn in history:
        prompt_messages.append({"role": turn["role"], "content": turn["content"]})
    prompt_messages.append({"role": "user", "content": user_query_text})
    prompt_messages.append({"role": "system", "content": f"Live MCP Server Output Result:\n{mcp_response_json}"})
    
    response = llm.invoke(prompt_messages)
    return {"final_output": response.content.strip()}

async def claims_specialist_node(state: AgentGraphState) -> dict:
    """Agent 3: Claims Specialist node utilizing conversation memory logs."""
    print("\n" + "="*15 + " 📄 NODE 3: CLAIMS ADJUDICATION EXPERT " + "="*15)
    groq_api_token = os.environ.get("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_token, model_name="llama-3.1-8b-instant", temperature=0.0)
    user_query_text = state.get("user_query", "")
    
    history, _ = load_session_history_and_plan(state.get("session_id", "DEFAULT-SESS"))
    
    claim_id = "CLM9901"
    if "clm9902" in user_query_text.lower(): claim_id = "CLM9902"
    elif "clm9903" in user_query_text.lower(): claim_id = "CLM9903"
    
    mcp_response_json = await call_mcp_tool("get_claim_status", {"claim_id": claim_id})
    
    instruction_prompt = (
        "Context: You are an expert Health Insurance Claims Adjudication Specialist.\n"
        "Instruction: Report the processing status, financial tracking, and denials with literal precision."
    )
    
    prompt_messages = [{"role": "system", "content": instruction_prompt}]
    for turn in history:
        prompt_messages.append({"role": turn["role"], "content": turn["content"]})
    prompt_messages.append({"role": "user", "content": user_query_text})
    prompt_messages.append({"role": "system", "content": f"Live MCP Server Output Result:\n{mcp_response_json}"})
    
    response = llm.invoke(prompt_messages)
    return {"final_output": response.content.strip()}

async def enrollment_handler_node(state: AgentGraphState) -> dict:
    """Agent 4: Enrollment handler node."""
    print("\n" + "="*15 + " 📋 NODE 4: ENROLLMENT GATEWAY HANDLER " + "="*15)
    return {"final_output": "Enrollment inquiries and premium schedules are managed securely via our separate Corporate HR gateway portal."}

# ----------------------------------------------------------------------
# 5. ASSEMBLE GRAPH WORKFLOW MATRIX
# ----------------------------------------------------------------------
workflow_graph = StateGraph(AgentGraphState)
workflow_graph.add_node("SupervisorRouter", router_node)
workflow_graph.add_node("CoverageSpecialist", coverage_specialist_node)
workflow_graph.add_node("ClaimsSpecialist", claims_specialist_node)
workflow_graph.add_node("EnrollmentHandler", enrollment_handler_node)

workflow_graph.add_edge(START, "SupervisorRouter")
workflow_graph.add_conditional_edges(
    "SupervisorRouter",
    lambda state: state.get("next_node", "EnrollmentHandler"),
    {
        "CoverageSpecialist": "CoverageSpecialist",
        "ClaimsSpecialist": "ClaimsSpecialist",
        "EnrollmentHandler": "EnrollmentHandler"
    }
)
workflow_graph.add_edge("CoverageSpecialist", END)
workflow_graph.add_edge("ClaimsSpecialist", END)
workflow_graph.add_edge("EnrollmentHandler", END)

multi_agent_application_mesh = workflow_graph.compile()

# ----------------------------------------------------------------------
# ASYNCHRONOUS CONSOLE LOOP RUNNER BLOCK
# ----------------------------------------------------------------------
async def main_async_loop():
    print("=" * 60)
    print("🕸️ MEMORY-RICH MCP MULTI-AGENT STATE GRAPH ACTIVE")
    print("Type your insurance question and press Enter. Type 'exit' to quit.")
    print("=" * 60)
    
    # Establish a fixed session tracking tag descriptor to pull matching SQLite histories
    SESSION_ID_TAG = "CHAT-PERSIST-99"

    while True:
        try:
            user_input = await asyncio.to_thread(input, "\nYou: ")
            user_input = user_input.strip()
            if not user_input or user_input.lower() in ["exit", "quit", "q"]:
                break
                
            # Pre-load incoming turns into database to ensure history records track properly
            try:
                from datetime import datetime, timezone
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (SESSION_ID_TAG, "user", user_input, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                )
                conn.commit()
                conn.close()
            except Exception:
                pass

            initial_state: AgentGraphState = {
                "user_query": user_input,
                "messages": [],
                "next_node": "",
                "final_output": "",
                "session_id": SESSION_ID_TAG
            }
            
            final_computed_state = await multi_agent_application_mesh.ainvoke(initial_state)
            ans = final_computed_state.get("final_output", "Error processing.")
            
            # Save assistant's answer down to disk logs
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (SESSION_ID_TAG, "assistant", ans, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                )
                conn.commit()
                conn.close()
            except Exception:
                pass
            
            print("\n" + "="*15 + " FINAL AGENT ANSWER SYSTEM OUTPUT " + "="*15)
            print(ans)
            print("="*60 + "\n")
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    asyncio.run(main_async_loop())