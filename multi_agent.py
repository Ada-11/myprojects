import os
import sys
import json
import sqlite3
import asyncio
from datetime import datetime
from typing import Literal, TypedDict, List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

# --- INITIALIZE ---
load_dotenv()
from langfuse import Langfuse
langfuse = Langfuse()

ACTIVE_MODEL = "openai/gpt-oss-20b"
DB_PATH = "/app/coverage-chatbot-api/coverage.db"
if not os.path.exists(DB_PATH):
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
    card_type: Optional[str]
    card_payload: Optional[dict]

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
        
        p_id = None
        if "silver" in query or "p102" in query:
            p_id = "P102"
        elif "gold" in query or "p101" in query:
            p_id = "P101"
        else:
            p_id = "P101" if "gold" in history_plan.lower() else "P102" if "silver" in history_plan.lower() else "P101"

        proc = "deductible" if "deductible" in query else "general coverage"
        mcp_res = await call_mcp_tool("check_coverage", {"plan_id": p_id, "procedure": proc})
        
        ui_card_payload = None
        try:
            parsed = json.loads(mcp_res)
            raw_deductible = parsed.get("annual_deductible_impact", "0").replace("$", "").replace(",", "")
            ui_card_payload = {
                "plan_name": parsed.get("verified_plan_name", "Insurance Plan"),
                "deductible": float(raw_deductible),
                "copay": parsed.get("member_copay_coinsurance_rate", "N/A"),
                "covered": "not covered" not in parsed.get("vector_grounded_notes", "").lower()
            }
        except: pass

        llm = ChatGroq(model_name=ACTIVE_MODEL, temperature=0.0)
        prompt = [
            {"role": "system", "content": (
                "You are an Elite Policy Reporter. Summarize provided data.\n"
                "STRIKE FORCE RULE: Talk text only. DO NOT output JSON. DO NOT call tools.\n"
                f"DATA: {mcp_res}\n"
                "Conclude with: 'This is a structural coverage determination. Not medical advice.'"
            )},
            *history,
            {"role": "user", "content": state["user_query"]}
        ]
        
        response = llm.invoke(prompt)
        span.update(output=response.content)
        return {
            "final_output": response.content.strip(), 
            "card_type": "coverage", 
            "card_payload": ui_card_payload
        }

async def claims_specialist_node(state: AgentGraphState) -> dict:
    with langfuse.start_as_current_observation(name="claims_expert") as span:
        history, _ = load_session_history_and_plan(state["session_id"])
        c_id = "CLM9901"
        if "clm9902" in state["user_query"].lower(): c_id = "CLM9902"
        
        mcp_res = await call_mcp_tool("get_claim_status", {"claim_id": c_id})
        
        ui_card_payload = None
        try:
            parsed = json.loads(mcp_res)
            raw_amt = parsed.get("submitted_financial_amount", "0").replace("$", "").replace(",", "")
            ui_card_payload = {
                "claim_id": c_id,
                "status": parsed.get("adjudication_state_status", "pending").lower(),
                "amount": float(raw_amt),
                "date": "2026-08-24"
            }
        except: pass

        llm = ChatGroq(model_name=ACTIVE_MODEL, temperature=0.0)
        prompt = [
            {"role": "system", "content": "Claims Expert. Summarize provided data. No JSON. No tools.\n" + f"DATA: {mcp_res}"},
            *history,
            {"role": "user", "content": state["user_query"]}
        ]
        response = llm.invoke(prompt)
        span.update(output=response.content)
        return {
            "final_output": response.content.strip(), 
            "card_type": "claim", 
            "card_payload": ui_card_payload
        }

async def enrollment_handler_node(state: AgentGraphState) -> dict:
    # UPDATED PHRASE BELOW:
    new_phrase = "Enrollment inquiries and member ID requests are managed via the official secure HR Portal. Please log in to your dashboard to complete these updates."
    
    return {
        "final_output": new_phrase, 
        "card_type": None, 
        "card_payload": None
    }

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