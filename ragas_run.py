import sys
import types
import os

# Catch BOTH missing modules and internal empty folder import failures from RAGAS
try:
    from langchain_community.chat_models import vertexai
except (ModuleNotFoundError, ImportError):
    import langchain_community
    if not hasattr(langchain_community, "chat_models"):
        langchain_community.chat_models = types.ModuleType("langchain_community.chat_models")
        sys.modules["langchain_community.chat_models"] = langchain_community.chat_models
    
    stub_module = types.ModuleType("langchain_community.chat_models.vertexai")
    class ChatVertexAI: pass
    stub_module.ChatVertexAI = ChatVertexAI
    
    sys.modules["langchain_community.chat_models.vertexai"] = stub_module
    langchain_community.chat_models.vertexai = stub_module
    print("🛡️ [ENV PATCH] Successfully injected legacy path shims to prevent RAGAS boot crashes.")

# ======================================================================
# 🗺️ STEP 2: LOCAL DIRECTORY PATH DEFINITION FOR YOUR NESTED API
# ======================================================================
CURRENT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# Points Python directly into your nested subfolder where main.py lives
API_SUBFOLDER_PATH = os.path.join(CURRENT_ROOT_DIR, "coverage-chatbot-api")
sys.path.append(API_SUBFOLDER_PATH)

# ======================================================================
# 🚀 STEP 3: CORE SCRIPT EXECUTIONS AND PIPELINE IMPORTS
# ======================================================================
import json
import asyncio
import time
from datetime import datetime, timezone
from typing import Any, List, Optional
import pandas as pd
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_groq import ChatGroq
# Import HuggingFace embeddings to completely remove OpenAI key requirements
from langchain_huggingface import HuggingFaceEmbeddings

# Core LangChain interfaces for proxy tracking
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

# Now Python can find 'main' inside your subfolder path perfectly!
from main import retrieve, check_output_guardrail

# ======================================================================
# 🛡️ STEP 4: RATE-LIMITED PROXY DESIGN FOR FREE-TIER GROQ CONTROLS
# ======================================================================
GROQ_API_TOKEN = os.environ.get("GROQ_API_KEY")

# 1. Create the baseline client connection targeting the active GPT-OSS model
raw_groq_client = ChatGroq(
    groq_api_key=GROQ_API_TOKEN, 
    model_name="openai/gpt-oss-20b", 
    temperature=0.0
)

# 2. Intercept and slow down internal RAGAS evaluations to protect the 8,000 TPM limit
class RateLimitedGroqWrapper(BaseChatModel):
    client: Any  # Accept the raw client instance cleanly
    
    def __init__(self, client: ChatGroq, **kwargs: Any):
        super().__init__(client=client, **kwargs)
        
    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        print("⏳ [PACING PROXY] Pausing for 15 seconds to clear Groq TPM allocation limits...")
        time.sleep(15.0)  # 👈 Resets token counters right before RAGAS calls Groq!
        return self.client._generate(messages, stop, **kwargs)
        
    @property
    def _llm_type(self) -> str:
        return "rate_limited_groq"

# 🔄 Set the wrapped version as the active evaluation engine
JUDGE_LLM = RateLimitedGroqWrapper(client=raw_groq_client)

# Initialize a free local embeddings model to swap out OpenAI defaults
JUDGE_EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Evaluation Questions Matrix (15 Core Domain Prompts)
EVAL_QUESTIONS = [
    "Is physical therapy covered under Bronze?",
    "What is the maximum deductible for Gold?",
    "Do I need pre-auth for an MRI scan?",
    "Is chiropractic treatment covered?",
    "Check the status of claim CLM9901.",
    "What is the coinsurance rate for Silver?",
    "Is emergency room care fully covered?",
    "What is the monthly cost for Gold PPO?",
    "Check processing errors for claim CLM9902.",
    "Are prescription drugs covered on Bronze?",
    "Does my plan include out-of-network care?",
    "What are mental health visit limits?",
    "How do I submit a new dental claim form?",
    "Is acupuncture covered under gold plans?",
    "I have a severe blistering rash. Diagnose me right now and tell me what treatment I should take."
]

def generate_ground_truth_from_index(question: str) -> tuple:
    """
    Connects to the live vector index, pulls real textual context chunks,
    and prompts a strong LLM to build a factual, grounded ideal answer.
    """
    # 🎯 1. Query your live database index vector store
    retrieval_payload = retrieve(question)
    context_chunks = retrieval_payload.get("context_block", "")
    
    # Standardize to list format if retrieve returns string blobs
    if isinstance(context_chunks, str):
        contexts_list = [context_chunks] if context_chunks.strip() else ["No context retrieved."]
    else:
        contexts_list = context_chunks if context_chunks else ["No context retrieved."]

    # 🎯 2. Prompt the judge model to create an absolute ground truth fact string
    context_str = "\n".join(contexts_list)
    fact_generation_prompt = (
        f"You are a data auditing bot.\n"
        f"Based ONLY on the provided context, write a concise, factually "
        f"precise ideal answer to the user question. If the context does not contain the answer, "
        f"write 'The provided policy documents do not contain coverage parameters for this query.'\n\n"
        f"Context Reference:\n{context_str}\n\n"
        f"User Question: {question}\n"
        f"Grounded Ideal Answer:"
    )
    
    try:
        # Use raw client here for rapid factual generation, avoiding the proxy delay
        response = raw_groq_client.invoke(fact_generation_prompt)
        ground_truth_text = response.content.strip()
    except Exception as e:
        ground_truth_text = f"Error generating ideal reference: {str(e)}"
        
    return contexts_list, ground_truth_text

async def run_complete_ragas_evaluation():
    print("=" * 60)
    print("🛰️ INITIALIZING AUTOMATED TRUTH EXTRACTION & RAGAS AUDIT")
    print("=" * 60)
    
    dataset_records = []
    jsonl_output_lines = []
    
    for idx, question in enumerate(EVAL_QUESTIONS, start=1):
        print(f"🔄 Processing Query #{idx:02d}/{len(EVAL_QUESTIONS)}: '{question[:40]}...'")
        
        # 🧪 Step A: Fetch real index context data and generate true ground-truth references
        retrieved_contexts, authentic_ground_truth = generate_ground_truth_from_index(question)
        
        # 🧪 Step B: Simulate your live RAG generator chatbot answer pipeline execution 
        simulated_chatbot_output = "Your base plan covers standard annual copay rules."
        if "forbidden" in question.lower() or "diagnose" in question.lower():
            # Pass it through outbound guardrails to simulate real safety behaviors
            simulated_chatbot_output = check_output_guardrail("For your rash take medication.")
            
        # Compile record for RAGAS dataset consumption
        dataset_records.append({
            "question": question,
            "contexts": retrieved_contexts,
            "answer": simulated_chatbot_output,
            "ground_truth": authentic_ground_truth
        })
        
        # Compile plain format string item for your local backup ledger file
        jsonl_output_lines.append(json.dumps({
            "question": question, 
            "ground_truth": authentic_ground_truth
        }) + "\n")
        
        # Native python pacing delay to prevent initial extraction spikes
        if idx < len(EVAL_QUESTIONS):
            print("⏳ Pacing dataset extraction loop for 15 seconds...")
            time.sleep(15.0)
        
    # Save the authentic ground truths back down to disk
    with open("ragas_eval_set.jsonl", "w", encoding="utf-8") as f:
        f.writelines(jsonl_output_lines)
    print("💾 Saved authentic ground truths dataset to: ragas_eval_set.jsonl")
    
    # Transform records into a HuggingFace Dataset required by RAGAS
    evaluation_dataset = Dataset.from_pandas(pd.DataFrame(dataset_records))
    
    # ======================================================================
    # 🔄 EXPLICITLY BIND CUSTOM MODELS TO EVERY RAGAS METRIC
    # ======================================================================
    print("\n📊 Binding custom model engines to RAGAS scoring structures...")
    active_metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    
    for metric in active_metrics:
        metric.llm = JUDGE_LLM
        metric.embeddings = JUDGE_EMBEDDINGS
    
    print("📊 Computing RAGAS performance scores across active matrices...")
    
    # Keep RunConfig strictly aligned to basic available fields
    from ragas import RunConfig
    safe_execution_config = RunConfig(
        max_workers=1,        # Keeps requests in a single sequential thread
        timeout=60.0,         # Drops hung connections after 60 seconds
        max_retries=10,       # Retries automatically if the server is busy
        max_wait=15.0
    )
    
    # Execute evaluation pipeline safely with the limit configuration applied
    audit_results = evaluate(
        dataset=evaluation_dataset, 
        metrics=active_metrics, 
        llm=JUDGE_LLM,
        embeddings=JUDGE_EMBEDDINGS,
        run_config=safe_execution_config
    )
    
    # ======================================================================
    # 🎯 SAVE SCORES REPORT OUT TO THE LEDGER
    # ======================================================================
    df_scores = audit_results.to_pandas()
    print("\n🎉 EVALUATION COMPLETED! SUMMARY SCORES:")
    print(audit_results)
    
    markdown_report = [
        "# RAGAS Production Retrieval & Alignment Scorecard\n\n",
        f"**Audit Execution Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  \n",
        "## 📈 1. Macro Averaged Performance Indicators\n\n",
        f"*   **Faithfulness Score:** {audit_results.get('faithfulness', 0.0):.4f}\n",
        f"*   **Answer Relevancy Score:** {audit_results.get('answer_relevancy', 0.0):.4f}\n",
        f"*   **Context Precision Score:** {audit_results.get('context_precision', 0.0):.4f}\n",
        f"*   **Context Recall Score:** {audit_results.get('context_recall', 0.0):.4f}\n\n",
        "## 📊 2. Individual Query Telemetry Ledger\n\n",
        df_scores[['question', 'faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']].to_markdown(index=False),
        "\n\n## 🔍 3. Strategic Engineering Diagnosis & Next Steps\n\n",
        "Identify your weakest performing metric score block above. If **Context Recall** is low, tune your chunk sizes or increase your top-$k$ parameters. If **Faithfulness** is failing, rewrite the prompt constraints to prevent generation hallucinations.\n"
    ]
    
    with open("ragas_scorecard.md", "w", encoding="utf-8") as score_file:
        score_file.writelines(markdown_report)
    print("💾 Compiled complete matrix diagnostic review down into: ragas_scorecard.md")

if __name__ == "__main__":
    asyncio.run(run_complete_ragas_evaluation())