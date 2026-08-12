import os
import sys
import json
from typing import Literal, TypedDict, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

# Import LangGraph workflow assembly models
from langgraph.graph import StateGraph, START, END

# Ensure parent directory is accessible for local module resolutions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tool_calling_chatbot import (
    check_coverage as native_check_coverage,
    get_claim_status as native_get_claim_status
)

# ----------------------------------------------------------------------
# 1. STATE MANAGEMENT INTERFACE CONTRACT
# ----------------------------------------------------------------------
class AgentGraphState(TypedDict):
    """Unified state tracking matrix passed across graph nodes."""
    messages: List[dict]
    next_node: str
    user_query: str
    final_output: str

class RouteDecision(BaseModel):
    """Structured Pydantic contract enforcing deterministic routing paths."""
    intent_classification: Literal["coverage", "claims", "enrollment"]
    next_action_node: Literal["CoverageSpecialist", "ClaimsSpecialist", "EnrollmentHandler"]
    routing_reasoning: str

# ----------------------------------------------------------------------
# 2. GRAPH WORKFLOW NODE AGENT ENGINES
# ----------------------------------------------------------------------
def router_node(state: AgentGraphState) -> dict:
    """Supervisor Router: Classifies user intent and sets the target lane."""
    print("\n" + "="*15 + " 🔀 NODE 1: SUPERVISOR ROUTER " + "="*15)
    groq_api_token = os.environ.get("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_token, model_name="llama-3.1-8b-instant", temperature=0.0)
    structured_router = llm.with_structured_output(RouteDecision)
    
    system_prompt = (
        "Analyze the query and pick the single best specialist agent node.\n"
        "MAPPING RULES:\n"
        "1. Policy rules, inclusions, visit limits -> route to 'CoverageSpecialist'.\n"
        "2. Claims state, paid amounts, denials, billing -> route to 'ClaimsSpecialist'.\n"
        "3. Premium costs, HR setup, enrollments -> route to 'EnrollmentHandler'."
    )
    user_query_text = state.get("user_query", "")
    routing_result: RouteDecision = structured_router.invoke(f"{system_prompt}\n\nUser Query: {user_query_text}")
    
    print(f"▶ Target Specialist Selected: `{routing_result.next_action_node}`")
    print(f"▶ Reason: *{routing_result.routing_reasoning}*")
    return {"next_node": routing_result.next_action_node}

def coverage_specialist_node(state: AgentGraphState) -> dict:
    """Agent 2: Coverage Specialist node."""
    print("\n" + "="*15 + " 🛡️ NODE 2: POLICY COVERAGE EXPERT " + "="*15)
    groq_api_token = os.environ.get("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_token, model_name="llama-3.1-8b-instant", temperature=0.0)
    user_query_text = state.get("user_query", "")
    
    plan_id = "P101"
    if "p102" in user_query_text.lower(): plan_id = "P102"
    elif "p103" in user_query_text.lower(): plan_id = "P103"
    
    procedure = "physical therapy"
    if "acupuncture" in user_query_text.lower(): procedure = "acupuncture"
    elif "mri" in user_query_text.lower(): procedure = "mri scan"
    
    tool_raw_data = native_check_coverage(plan_id=plan_id, procedure=procedure)
    
    instruction_prompt = (
        "Context: You are an elite Health Insurance Policy Coverage Specialist.\n"
        "Instruction: Summarize procedure coverage rules accurately from the tool data.\n"
        "Conclude with this exact disclaimer: 'This is a structural coverage determination based on exact policy terms. This is not medical advice.'"
    )
    response = llm.invoke(f"{instruction_prompt}\n\nQuery: {user_query_text}\n\nTool Output: {tool_raw_data}")
    return {"final_output": response.content.strip()}

def claims_specialist_node(state: AgentGraphState) -> dict:
    """Agent 3: Claims Specialist node."""
    print("\n" + "="*15 + " 📄 NODE 3: CLAIMS ADJUDICATION EXPERT " + "="*15)
    groq_api_token = os.environ.get("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_token, model_name="llama-3.1-8b-instant", temperature=0.0)
    user_query_text = state.get("user_query", "")
    
    claim_id = "CLM9901"
    if "clm9902" in user_query_text.lower(): claim_id = "CLM9902"
    elif "clm9903" in user_query_text.lower(): claim_id = "CLM9903"
    
    tool_raw_data = native_get_claim_status(claim_id=claim_id)
    
    instruction_prompt = (
        "Context: You are an expert Health Insurance Claims Adjudication Specialist.\n"
        "Instruction: Report the processing status, financial tracking, and denials with literal precision."
    )
    response = llm.invoke(f"{instruction_prompt}\n\nQuery: {user_query_text}\n\nTool Output: {tool_raw_data}")
    return {"final_output": response.content.strip()}

def enrollment_handler_node(state: AgentGraphState) -> dict:
    """Agent 4: Enrollment and Premium fallback handler node."""
    print("\n" + "="*15 + " 📋 NODE 4: ENROLLMENT GATEWAY HANDLER " + "="*15)
    return {"final_output": "Enrollment inquiries and premium schedules are managed securely via our separate Corporate HR gateway portal."}

# ----------------------------------------------------------------------
# 3. BUILD THE GRAPH WORKFLOW MATRIX LAYOUT
# ----------------------------------------------------------------------
workflow_graph = StateGraph(AgentGraphState)

# Mount our independent worker agents as operational graph nodes
workflow_graph.add_node("SupervisorRouter", router_node)
workflow_graph.add_node("CoverageSpecialist", coverage_specialist_node)
workflow_graph.add_node("ClaimsSpecialist", claims_specialist_node)
workflow_graph.add_node("EnrollmentHandler", enrollment_handler_node)

# Set the primary onboarding ingress edge entry gate
workflow_graph.add_edge(START, "SupervisorRouter")

# Define the dynamic routing router branch logic function
def condition_router_edge(state: AgentGraphState) -> str:
    """Acts as an active switcher directing traffic based on router state tags."""
    return state.get("next_node", "EnrollmentHandler")

# Wire the conditional routing edge to map traffic from the router to specialists
workflow_graph.add_conditional_edges(
    "SupervisorRouter",
    condition_router_edge,
    {
        "CoverageSpecialist": "CoverageSpecialist",
        "ClaimsSpecialist": "ClaimsSpecialist",
        "EnrollmentHandler": "EnrollmentHandler"
    }
)

# Connect specialist termination endpoints directly to graph conclusion matrix slots
workflow_graph.add_edge("CoverageSpecialist", END)
workflow_graph.add_edge("ClaimsSpecialist", END)
workflow_graph.add_edge("EnrollmentHandler", END)

# Compile the multi-agent state graph into an executable blueprint app node
multi_agent_application_mesh = workflow_graph.compile()

# ----------------------------------------------------------------------
# INTERACTIVE TERMINAL LOOP RUNNER
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("🕸️ MULTI-AGENT STATE GRAPH GRAPH COORDINATOR SYSTEM ACTIVE")
    print("Type your insurance question and press Enter. Type 'exit' to quit.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input or user_input.lower() in ["exit", "quit", "q"]:
                break
                
            # Initialize state structure payload mapping keys
            initial_state: AgentGraphState = {
                "user_query": user_input,
                "messages": [],
                "next_node": "",
                "final_output": ""
            }
            
            # Fire graph execution
            final_computed_state = multi_agent_application_mesh.invoke(initial_state)
            
            print("\n" + "="*15 + " FINAL AGENT ANSWER SYSTEM OUTPUT " + "="*15)
            print(final_computed_state.get("final_output", "Error compiling response."))
            print("="*60 + "\n")
            
        except KeyboardInterrupt:
            break
