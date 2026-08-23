import os
import sys
import json
import sqlite3
import asyncio
from typing import Literal, TypedDict, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

# --- INITIALIZE ---
load_dotenv()
from langfuse import Langfuse
langfuse = Langfuse()

ACTIVE_MODEL = "openai/gpt-oss-20b"
# Use absolute path for K8s, relative for local
DB_PATH = "/app/coverage-chatbot-api/coverage.db"
if not os.path.exists("/app"):
    DB_PATH = "coverage-chatbot-api/coverage.db"

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from guardrails_config import check_input_guardrail, check_output_guardrail

# ---------------------------------------------------------
# 1. STATE & ROUTING CONTRACTS
# ---------------------------------------------------------
class AgentGraphState(TypedDict):
    messages: List[dict]
    next_node: str
    user_query: str
    final_output: str
    session_id: str 

class RouteDecision(BaseModel):
    intent_classification: Literal["coverage", "claims", "enrollment"]
    next_action_node: Literal["CoverageSpecialist", "ClaimsSpecialist", "EnrollmentHandler"]
    routing_reasoning: str

# ---------------------------------------------------------
# 2. UTILITIES
# ---------------------------------------------------------
def load_session_history_and_plan(session_id: str) -> tuple:
    historical_turns = []
    remembered_plan_id = "Not Specified Yet"
    if not os.path.exists(DB_PATH): return [], remembered_plan_id
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id ASC", (session_id,))
        rows = cursor.fetchall(); conn.close()
        for role, content in rows:
            historical_turns.append({"role": role, "content": content})
            c_up = content.upper()
            if "P101" in c_up or "GOLD" in c_up: remembered_plan_id = "P101 (Gold PPO)"
            elif "P102" in c_up or "SILVER" in c_up: remembered_plan_id = "P102 (Silver HMO)"
    except Exception: pass
    return historical_turns[-10:], remembered_plan_id

async def call_mcp_tool(tool_name: str, tool_args: dict) -> str:
    with langfuse.start_as_current_observation(name=f"mcp_{tool_name}", input=tool_args) as span:
        server_params = StdioServerParameters(
            command=sys.executable, 
            args=[os.path.join(os.getcwd(), "mcp_server.py")]
        )
        try:
            async with asyncio.timeout(10.0):
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments=tool_args)
                        output = result.content[0].text if result and result.content else "No Data Found"
                        span.update(output=output)
                        return output
        except Exception as e:
            span.update(level="ERROR", status_message=str(e))
            return "⚠️ Database connectivity error."

# ---------------------------------------------------------
# 3. NODES
# ---------------------------------------------------------
async def router_node(state: AgentGraphState) -> dict:
    with langfuse.start_as_current_observation(name="supervisor_router", input=state["user_query"]) as span:
        llm = ChatGroq(model_name=ACTIVE_MODEL, temperature=0.0)
        structured_router = llm.with_structured_output(RouteDecision)
        
        prompt = (
            "You are a routing supervisor. Categorize the query:\n"
            "1. Deductibles, copays, coverage limits, specific procedure costs -> 'CoverageSpecialist'\n"
            "2. Claims, payments, CLM IDs, denial reasons -> 'ClaimsSpecialist'\n"
            "3. Enrollment, portals, HR, member IDs -> 'EnrollmentHandler'\n"
            f"User Query: {state['user_query']}"
        )
        
        try:
            decision = structured_router.invoke(prompt)
            span.update(output=decision.next_action_node)
            return {"next_node": decision.next_action_node}
        except:
            return {"next_node": "EnrollmentHandler"}

async def coverage_specialist_node(state: AgentGraphState) -> dict:
    with langfuse.start_as_current_observation(name="coverage_expert") as span:
        query = state["user_query"].lower()
        history, history_plan = load_session_history_and_plan(state["session_id"])
        
        # PLAN IDENTIFICATION LOGIC
        p_id = "P101" # Default
        if "silver" in query or "p102" in query or "silver" in history_plan.lower():
            p_id = "P102"
        elif "gold" in query or "p101" in query or "gold" in history_plan.lower():
            p_id = "P101"

        # PROCEDURE IDENTIFICATION
        proc = "general coverage"
        if "deductible" in query: proc = "deductible"
        elif "copay" in query: proc = "copay"
        elif "mri" in query: proc = "mri scan"
        elif "cosmetic" in query: proc = "cosmetic procedure"
        elif "physical therapy" in query: proc = "physical therapy"

        # Step 1: Tool Call to the MCP Database
        mcp_res = await call_mcp_tool("check_coverage", {"plan_id": p_id, "procedure": proc})
        
        # Step 2: Professional Synthesis
        llm = ChatGroq(model_name=ACTIVE_MODEL, temperature=0.0)
        prompt = [
            {"role": "system", "content": (
                "You are an Elite Policy Coverage Reporter. Your task is to report the specific data retrieved from tools.\n"
                f"RETRIEVED TOOL DATA: {mcp_res}\n"
                "RULES:\n"
                "1. If the tool data provides a deductible or copay, state it clearly.\n"
                "2. If the tool says 'is_covered: False' or 'No record', explain that the specific item is not covered or requires manual support.\n"
                "3. Speak professionally. DO NOT mention tool calls. DO NOT output JSON.\n"
                "4. Conclude with: 'This is a structural coverage determination. Not medical advice.'"
            )},
            *history,
            {"role": "user", "content": state["user_query"]}
        ]
        
        try:
            response = llm.invoke(prompt)
            span.update(output=response.content)
            return {"final_output": response.content.strip()}
        except Exception:
            return {"final_output": f"Based on your policy ({p_id}), the data for {proc} indicates: {mcp_res}. Contact support at 1-800-555-0199 for more details."}

async def claims_specialist_node(state: AgentGraphState) -> dict:
    with langfuse.start_as_current_observation(name="claims_expert") as span:
        history, _ = load_session_history_and_plan(state["session_id"])
        
        # Extract Claim ID
        c_id = "CLM9901"
        if "clm9902" in state["user_query"].lower(): c_id = "CLM9902"
        elif "clm9903" in state["user_query"].lower(): c_id = "CLM9903"
        
        mcp_res = await call_mcp_tool("get_claim_status", {"claim_id": c_id})
        
        llm = ChatGroq(model_name=ACTIVE_MODEL, temperature=0.0)
        prompt = [
            {"role": "system", "content": "You are a Claims Adjudication reporter. Summarize the provided claim data. No tool calls or JSON."},
            *history,
            {"role": "user", "content": state["user_query"]},
            {"role": "system", "content": f"DATA: {mcp_res}"}
        ]
        response = llm.invoke(prompt)
        span.update(output=response.content)
        return {"final_output": response.content.strip()}

async def enrollment_handler_node(state: AgentGraphState) -> dict:
    with langfuse.start_as_current_observation(name="enrollment_handler") as span:
        res = "Enrollment inquiries and member ID requests are managed via the secure Corporate HR Portal. Please log in to your dashboard for those updates."
        span.update(output=res)
        return {"final_output": res}

# --- ASSEMBLE ---
workflow_graph = StateGraph(AgentGraphState)
workflow_graph.add_node("SupervisorRouter", router_node)
workflow_graph.add_node("CoverageSpecialist", coverage_specialist_node)
workflow_graph.add_node("ClaimsSpecialist", claims_specialist_node)
workflow_graph.add_node("EnrollmentHandler", enrollment_handler_node)
workflow_graph.add_edge(START, "SupervisorRouter")
workflow_graph.add_conditional_edges("SupervisorRouter", lambda s: s["next_node"])
workflow_graph.add_edge("CoverageSpecialist", END)
workflow_graph.add_edge("ClaimsSpecialist", END)
workflow_graph.add_edge("EnrollmentHandler", END)
multi_agent_application_mesh = workflow_graph.compile()

if __name__ == "__main__":
    async def run():
        print("🕸️ MULTI-AGENT STATE GRAPH CLI")
        res = await multi_agent_application_mesh.ainvoke({"user_query": "Deductible for gold?", "session_id": "CLI"})
        print(f"AI: {res['final_output']}")
        langfuse.flush()
    asyncio.run(run())