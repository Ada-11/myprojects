Retrospective: Agentic Chatbot Deployment & Stabilization
1. What Worked Well
Multi-Agent Orchestration (LangGraph): The decision to use LangGraph for state management was highly successful. It allowed for a clean separation between the Supervisor Router and specialized specialist nodes. This made it possible to pinpoint exactly where routing was failing and allowed for individual node-level prompt hardening.

Hybrid Retrieval (RAG): The integration of ChromaDB for unstructured policy documents and SQL-style lookups for structured plan data proved to be a robust strategy. The agent was able to provide high-precision answers regarding coinsurance and deductibles that outperformed standard LLM general knowledge.

2. What Was Harder Than Expected
Model Decommissioning (The 404 Trap): The sudden decommissioning of llama-3.1-8b-instant midway through the debugging phase forced an emergency migration to openai/gpt-oss-20b. This change revealed significant behavioral differences in "eager tool-calling," necessitating an immediate rewrite of the specialist node prompts to prevent HTTP 400 errors.
3. Starting Over: What I’d Do Differently
Implement "Manual First" Tracing: Relying on the "magic" of SDK decorators (@observe) proved fragile during dependency updates. Starting with manual span control would have provided more robust code that works across all versions of the SDK without requiring specific subfolder structures to be present.
Standardize Internal Data Bridges: I would define a stricter contract between the Agent and the UI earlier. By assuming the LLM could handle the visual data, we introduced "messy" output issues. Moving to a "Structured Bridge Pattern"—where the code extracts tool data into a fixed card_payload object—should be the default architectural choice for all future agentic projects.