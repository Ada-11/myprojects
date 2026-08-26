# 🚀 Agentic Health Insurance Navigator
Orion Member Portal - v2.0 Strategic Roadmap

Video link https://youtu.be/dPbu6lg-1ok

This document outlines the prioritized evolution of the Orion Agentic Chatbot from a containerized MVP to a production-scale, multi-modal healthcare navigation platform.

---

## 🟥 Phase 1: Critical Compliance & Governance (Immediate)
*Foundational requirement before transitioning from mock data to real member PHI.*

1. **Formal Legal & HIPAA Compliance Audit**
   - Conduct a comprehensive review of data handling, storage, and encryption.
   - Ensure "Business Associate Agreements" (BAA) are in place for cloud providers (Groq, Langfuse, Cloud Providers).
2. **SOC2 Type II Readiness**
   - Implement rigorous audit logging for every internal tool call and data retrieval.
   - Formalize the PII redaction pipeline (`redact_pii.py`) into a verified security layer.
3. **Identity & Access Management (IAM)**
   - Replace the UUID-based session tracking with a robust OAuth2/OpenID Connect provider (e.g., Auth0 or AWS Cognito).

---

## 🟦 Phase 2: Infrastructure & Cloud Scaling (Q1)
*Transitioning from local Minikube to managed production environments.*

1. **Managed Kubernetes (EKS/GKE/AKS)**
   - Migrate manifests to a managed cloud service for 99.9% uptime.
   - Implement **Horizontal Pod Autoscaling (HPA)** to handle traffic spikes during open enrollment.
2. **Cloud-Native Database Migration**
   - Migrate SQLite to a managed PostgreSQL instance (AWS RDS) with encrypted-at-rest volumes.
   - Transition ChromaDB to a managed Vector Store (Pinecone or PGVector) for global scaling.
3. **CI/CD Pipeline Integration**
   - Automated testing for guardrail regressions and RAGAS alignment scores before every deployment.

---

## 🟨 Phase 3: Multi-Modal Expansion (Q2)
*Enhancing member capabilities beyond simple text queries.*

1. **Multi-modal Document Processing (Vision)**
   - Support for **scanned document uploads** (EOBs, Medical Bills, Provider Letters).
   - Use Vision-LLMs (GPT-4o or Llama 3.2 Vision) to explain complex insurance terminology found in physical mail.
2. **Voice Input/Output (Accessibility)**
   - Integration of **Whisper (STT)** for hands-free queries.
   - Implementation of **Text-to-Speech (TTS)** for automated policy reading, enhancing accessibility for visually impaired members.

---

## 🟩 Phase 4: Globalization & Personalized Intelligence (Q3)
*Widening the funnel for diverse member populations.*

1. **Additional Language Support**
   - Native localization for Spanish, Mandarin, and Vietnamese to support diverse member bases.
   - Implementation of cross-lingual RAG (Retrieving English policy data and answering in the member's native language).
2. **Predictive Cost Estimation**
   - Utilizing historical claims data to predict out-of-pocket costs for upcoming procedures.
   - Proactive notifications: "Orion noticed you have a deductible remaining; here is how it affects your upcoming MRI."

---

## 🛠️ Tech Stack Evolution
| Component | v1 (Current) | v2 (Target) |
| :--- | :--- | :--- |
| **Orchestration** | Minikube (Local) | AWS EKS / Managed K8s |
| **Model** | GPT OSS 20B (Groq) | Hybrid (Llama 3.1 + GPT-4o Vision) |
| **Database** | SQLite / Local File | AWS RDS (Postgres) |
| **Vector Store** | ChromaDB (Local) | Pinecone / Weaviate |
| **Auth** | Session ID | OAuth2 / JWT |