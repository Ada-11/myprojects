# Health Insurance RAG Agent: Fine-Tuning Preparation & Boundary Analysis

**Project Subdirectory:** `/Users/ada/myprojects/my-first-app`  
**Target Architecture:** Schema Alignment, Liability Isolation, Tone Adaptation  

---

## 🧠 Structural Matrix: What Fine-Tuning Can vs. Cannot Fix

| Capability Profile | What Fine-Tuning CAN Fix / Enforce | What Fine-Tuning CANNOT Fix / Resolve |
| :--- | :--- | :--- |
| **System Tone & Persona** | **High Impact**: Locks in a rigid, non-conversational, clinical auditor persona or an empathetic navigator without relying on long system prompts. | **Irrelevant**: Cannot make a model behave safely if structural parameters leak due to loose code configurations. |
| **Output Schema Formatting** | **High Impact**: Trains the model to natively write output text payloads using rigid formatting conventions (like structural JSON blocks or `[ANALYSIS]` headers) with 100% predictability. | **Irrelevant**: Cannot fix structural parsing issues in the underlying application code loop parser. |
| **Liability Guardrails** | **High Impact**: Injects absolute compliance behavior, such as always ending responses with a mandated medical liability disclaimer or deflecting symptoms instantly. | **Dangerous Over-reliance**: Cannot prevent text generations from leaking incorrect data if the prompt lacks a grounded reference context layer. |
| **Policy Knowledge Base** | **Severe Violation / Anti-Pattern**: Do **not** use fine-tuning to update specific insurance premiums, deductible amounts, or coverage rules. | **Core Limitation**: The model will suffer from catastrophic forgetting and hallucinate outdated data when rates change. Dynamic variables must remain in the **RAG retrieval context layer**. |

---

## 🔍 Log File Audit: 3 Recurring System Issues Identified

Below is a diagnostic analysis of three common errors tracked in the runtime evaluation logs.

### Issue 1: Omission of Mandatory Liability Disclaimer / Conversational Tone Leakage
*   **Log Symptoms:** The model answers policy questions but forgets to attach the closing text block `"This is not medical advice"`. It also wastes tokens by leaking conversational chat filler into the stream (e.g., *"I would be delighted to look over your policy details today..."*).
*   **Root Cause:** Loose prompt guidance and standard base model instruction alignment drift.
*   **The Fix:** **Fine-Tuning CAN Fix This.** Fine-tuning the curated dataset (`fine_tune_train.jsonl`) modifies the model's base probability weights. It hardwires the model to always speak in an objective, concise auditor persona and instinctively attach the mandated liability suffix, regardless of user input.

### Issue 2: Empty Result Matrix for valid "Network Tier" lookups
*   **Log Symptoms:** When the user filters a query specifically for a valid plan option (e.g., `where={"network_tier": "silver"}`), the query tool returns zero results and outputs an empty markdown table layout.
*   **Root Cause:** **Retrieval Problem (Fine-Tuning Won't Fix This).** This is a data ingestion mismatch. The underlying database indexing code originally failed to extract columns from `plans.csv` or read case-sensitive inputs, saving attributes as `network_tier: "unknown"`.
*   **The Fix:** Fix the data ingestion python loop wrapper script (`upsert_chroma.py`) to correctly bind metadata columns before upserting into Chroma. No amount of fine-tuning can make an LLM retrieve missing or corrupted index fields.

### Issue 3: Chatbot "Conversational Trap" responses on Out-of-Bounds Queries
*   **Log Symptoms:** When asked an unindexed query (e.g., *"Is cosmetic root canal dental surgery covered?"*), the LLM responds with conversational chatter asking for clarification, rather than rejecting the question outright.
*   **Root Cause:** Prompt routing confusion. The LLM receives an empty context block string and falls back to its generic chat training weights.
*   **The Fix:** **Fine-Tuning CAN Fix This.** By training the model on out-of-bounds mapping pairs (like training case #7), the model learns that whenever the input `Context:` string block lacks matching keywords, it must immediately output the fixed fallback string: *"I don't know. The requested policy data is not present within your plan files."*

---

## 🎯 Fine-Tuning Strategy for this Program

1. **Objective**: Train a model to strictly ingest an arbitrary `Context` block, execute a structured reasoning step, enforce a formal tone, handle out-of-bounds questions with a fixed fallback string, and guarantee the presence of the mandated medical disclaimer.
2. **Data Split Protocol**:
   - Total Curated Repository (`fine_tune_dataset.jsonl`): 20 comprehensive base patterns.
   - Production Training Set (`fine_tune_train.jsonl`): 15 baseline examples + 10 structural variations (25 total entries) mapping standard and edge-case behaviors.
   - Held-Out Evaluation Set (`fine_tune_test.jsonl`): 5 distinct validation examples withheld entirely from training to measure structural generalization accuracy.
