import os
import asyncio
from typing import Literal, TypedDict, List
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langfuse import Langfuse
from dotenv import load_dotenv

load_dotenv()
langfuse = Langfuse()
ACTIVE_MODEL = "openai/gpt-oss-20b"

class AgentGraphState(TypedDict):
    user_query: str; next_node: str; final_output: str; session_id: str 

class RouteDecision(BaseModel):
    next_action_node: Literal["CoverageSpecialist", "EnrollmentHandler"]

async def router_node(state: AgentGraphState) -> dict:
    with langfuse.start_as_current_observation(name="node_router", input=state["user_query"]) as span:
        llm = ChatGroq(model_name=ACTIVE_MODEL, temperature=0.0)
        # In a real scenario, LLM would decide. Here we route to Coverage for test.
        decision = "CoverageSpecialist"
        span.update(output=decision)
        return {"next_node": decision}

async def coverage_specialist_node(state: AgentGraphState) -> dict:
    with langfuse.start_as_current_observation(name="node_coverage") as span:
        res = "Your P101 plan covers this visit. This is not medical advice."
        span.update(output=res)
        return {"final_output": res}

async def enrollment_handler_node(state: AgentGraphState) -> dict:
    return {"final_output": "Please contact HR."}

workflow_graph = StateGraph(AgentGraphState)
workflow_graph.add_node("SupervisorRouter", router_node)
workflow_graph.add_node("CoverageSpecialist", coverage_specialist_node)
workflow_graph.add_node("EnrollmentHandler", enrollment_handler_node)
workflow_graph.add_edge(START, "SupervisorRouter")
workflow_graph.add_conditional_edges("SupervisorRouter", lambda s: s["next_node"])
workflow_graph.add_edge("CoverageSpecialist", END)
workflow_graph.add_edge("EnrollmentHandler", END)

multi_agent_application_mesh = workflow_graph.compile()

if __name__ == "__main__":
    async def run():
        res = await multi_agent_application_mesh.ainvoke({"user_query": "Hello", "session_id": "CLI-TEST"})
        print(f"AI: {res['final_output']}")
        langfuse.flush()
    asyncio.run(run())