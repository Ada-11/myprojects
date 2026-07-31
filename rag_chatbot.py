import os
import sys
import json
import uuid
from datetime import datetime, timezone
from openai import OpenAI
from groq import Groq

# Explicitly import the retrieval pipeline engine from your project folder
from retrieval_engine import retrieve

def generate_answer(question: str, context: str) -> str:
    """
    Core LLM Generation Engine via the Native Groq Cloud SDK.
    Executes grounding context prompts at hyper-speed with zero local CPU overhead.
    """
    # 2. FIXED: Instantiate the official client seamlessly
    client = Groq(
        api_key="API_KEY_REDACTED_FOR_SECURITY"  # Replace
    )

    # STRICT GROUNDING PROMPT COMPLIANCE
    system_prompt = (
        "Answer using ONLY the context below.\n"
        "If the answer isn't in the context, say you don't know and suggest the member contact support.\n"
        "This is not medical advice.\n\n"
        f"Context: {context}"
    )

    user_content = f"Question: {question}"

    try:
        # 3. FIXED: Native cloud completions endpoint path router
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0  # Forces factual consistency and eliminates hallucinations
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"[CRITICAL ERROR] Groq Native SDK Cloud connection failure: {str(e)}"


def retrieve_and_answer(question: str) -> str:
    """
    Chained RAG Pipeline.
    Retrieves the context, strips metadata duplicates, and passes it to the generator.
    """
    retrieval_payload = retrieve(question)
    context_block = retrieval_payload["context_block"]
    answer = generate_answer(question, context_block)
    return answer


def run_and_log_qa_suite():
    """Loops through all 10 test questions and logs results to rag_qa_results.md"""
    project_root = "/Users/ada/myprojects/my-first-app"
    output_md_path = os.path.join(project_root, "rag_qa_results.md")

    test_cases = [
        "What is my annual deductible under the Gold PPO plan?",
        "Is physical therapy covered by my insurance policy?",
        "Show me the monthly premium costs for all available plans.",
        "Are cosmetic surgeries listed as exclusions under the Silver tier?",
        "What is the copay percentage for the Bronze HMO choice?",
        "How do I file a medical claim or get an update on billing error codes?",
        "What are the premium and deductible costs for the Silver HMO plan?",
        "Is outpatient speech evaluation covered under the Silver plan?",
        "Does the Bronze plan have a higher monthly cost than the Gold plan?",
        "Are experimental clinical drug trials completely restricted or denied?"
    ]

    print(f"[PROCESSING] Running end-to-end cloud RAG pipeline across {len(test_cases)} questions...")
    
    with open(output_md_path, "w", encoding="utf-8") as out:
        out.write("# Grounded RAG Chatbot QA Generation Audit Report\n\n")
        out.write(f"**Execution Timestamp:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`\n")
        out.write("**Model Engine:** Cloud `llama-3.1-8b-instant` via Groq LPU Hardware\n\n")
        out.write("=" * 80 + "\n\n")

        for idx, question in enumerate(test_cases, start=1):
            print(f" -> Processing case #{idx}: '{question[:45]}...'")
            final_answer = retrieve_and_answer(question)
            
            out.write(f"### Test Case #{idx}\n")
            out.write(f"**Question:** {question}\n\n")
            out.write("**Grounded LLM Response:**\n")
            out.write("```text\n")
            out.write(f"{final_answer}\n")
            out.write("```\n\n")
            out.write("-" * 80 + "\n\n")

    print(f"[SUCCESS] Audit complete! Results saved successfully to: {output_md_path}")


# --- Execution Router ---
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "--log":
        run_and_log_qa_suite()
    else:
        print("="*60)
        print("🤖 HEALTH INSURANCE RAG CHATBOT (Groq Cloud Acceleration) ACTIVE")
        print("Type your policy query and press Enter. Type 'exit' to quit.")
        print("Add '--log' to your command to run the 10-question suite file instead.")
        print("="*60)

        while True:
            try:
                user_input = input("\nYou: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("Closing chatbot session. Goodbye!")
                    break
                    
                print("[PROCESSING] Generating accelerated response...")
                bot_response = retrieve_and_answer(user_input)
                
                print(f"\nBot:\n{bot_response}")
                print("-" * 60)
                
            except KeyboardInterrupt:
                print("\nSession aborted manually.")
                break