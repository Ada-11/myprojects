This project is a Production-Grade Agentic RAG (Retrieval-Augmented Generation) System designed to help users navigate complex health insurance policies and claims. It utilizes a multi-agent orchestration layer to provide high-precision answers, visual UI components, and enterprise-level observability.

Video link https://youtu.be/dPbu6lg-1ok

🛡️ Agentic Health Insurance Navigator
🚀 Project Overview
The Navigator is built to solve the "black box" problem of health insurance. By combining LangGraph orchestration with a Hybrid Retrieval strategy, the system can distinguish between general policy questions (unstructured data) and specific plan metrics like deductibles and copays (structured data).

Key Features
Multi-Agent Orchestration: A Supervisor Router directs queries to specialized nodes (Coverage, Claims, or Enrollment).
Hybrid RAG Engine: Simultaneous semantic search via ChromaDB and relational lookups via SQL/CSV.
Visual UI Cards: Rich frontend experience using Streamlit that renders interactive cards for claim status and coverage summaries.
Enterprise Observability: Full lifecycle tracing using Langfuse v4, capturing latency, token usage, and cost analytics.
Hardened Security: Inbound and outbound guardrails to prevent PII leakage and unauthorized medical diagnostic advice.

🏗️ Technical Architecture
1. The Logic Layer (multi_agent.py)
Built on LangGraph, the system operates as a state machine:
Supervisor Router: Uses openai/gpt-oss-20b to classify intent.
Specialist Nodes: Specialized agents that execute "Tool-Use" logic to fetch data from the Knowledge Base.
Structured Bridge: Manually extracts tool data into a card_payload to ensure the UI remains visually rich.

2. The Retrieval Engine (retrieval_engine.py & mcp_server.py)
Unstructured: Policy PDFs and TXT files are chunked, embedded using all-MiniLM-L6-v2, and stored in ChromaDB.
Structured: Relational plan data (plans.csv) is queried via a chaos-defended MCP (Model Context Protocol) server.

3. The API Gateway (main.py)
A FastAPI server that handles:
SSE Streaming: Provides real-time token delivery to the frontend.
SHA-256 Caching: Dramatically reduces costs by caching general policy answers.
Telemetry: Logs every transaction and its associated cost to a persistent SQLite database.

📦 Infrastructure & Deployment
The project is fully containerized and orchestrated for high availability:
Docker: Multi-stage builds for a slim 3.11-slim runtime environment.
Kubernetes (Minikube):
Deployments: Redundant backend pods (replicas) for zero-downtime rollouts.
Secrets: Secure injection of Groq and Langfuse API keys.
Probes: Liveness and Readiness probes ensure the backend has loaded heavy ML models before accepting traffic.



### 📄 Project repo structure

<details>
<summary>Project repo structure</summary>

```program-repo/
├── k8s/                         # Kubernetes manifests (Deployments, Services)
├── coverage-chatbot-api/        # Core Data (coverage.db, plans.csv)
├── main.py                      # FastAPI Streaming SSE Gateway
├── multi_agent.py               # LangGraph Orchestration & Node Logic
├── tool_calling_chatbot.py      # LLM Inference & Memory Compression
├── retrieval_engine.py          # Hybrid RAG Coordination
├── guardrails_config.py         # Security & Medical Deflection
├── app.py                       # Streamlit Frontend UI
├── Dockerfile                   # Multi-stage Backend Build
└── .dockerignore                # Critical for cluster performance
```

</details>


🛠️ Observability & Debugging
The system is integrated with Langfuse v4 using a manual stateful client approach. This provides a "thought-trace" for every user query, showing exactly how the Supervisor decided on a route and how the Specialist formulated the answer.
Latency Monitoring: Every tool call and LLM turn is timed.

Cost Tracking: Real-time token counting via tiktoken mapped to USD pricing.
Health Dashboard: Accessible via /health for cluster monitoring.

🧪 Quick Start (Local Mac)
Environment: Ensure Python 3.11.
Keys: Export GROQ_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST.
Run API: python main.py --server
Run UI: streamlit run app.py

📝 Compliance Note
This system is a structural coverage determination tool based on exact policy terms. It is strictly forbidden from providing clinical or diagnostic medical advice.