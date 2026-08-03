import os
import sys
import json
from datetime import datetime, timezone
from groq import Groq

# Import schemas and functions from your primary chatbot engine file
from tool_calling_chatbot import TOOLS_SCHEMAS

# ---------------------------------------------------------
# 1. CORE DEFINITIONS: THE 6 SPECIFIC TEST QUESTIONS
# ---------------------------------------------------------
TEST_SUITE = [
    {
        "id": 1,
        "question": "Is physical therapy covered under my plan P101?",
        "expected_tool": "check_coverage"
    },
    {
        "id": 2,
        "question": "Can you check if my claim CLM9902 has been processed or paid yet?",
        "expected_tool": "get_claim_status"
    },
    {
        "id": 3,
        "question": "What is the annual deductible and monthly premium for plan P102?",
        "expected_tool": "get_plan_details"
    },
    {
        "id": 4,
        "question": "How much will I pay out-of-pocket for knee surgery under my plan P101?",
        "expected_tool": "estimate_out_of_pocket_cost"
    },
    {
        "id": 5,
        "question": "I want to look up my coverage for routine evaluations under plan P102 and also check the deductible details for plan P102.",
        "expected_tool": "MULTIPLE (check_coverage + get_plan_details)"
    },
    {
        "id": 6,
        "question": "Hi, I am stressed about my medical bills. Can you tell me a joke to cheer me up?",
        "expected_tool": "NONE (Conversational Fallback)"
    }
]

def execute_tool_selection_audit():
    api_key_env = os.environ.get("GROQ_API_KEY")
    if not api_key_env:
        print("[ERROR] GROQ_API_KEY environment variable not set. Run 'export GROQ_API_KEY=...' first.")
        return

    client = Groq(api_key=api_key_env)
    output_md_path = "/Users/ada/myprojects/my-first-app/tool_call_log.md"

    print(f"[PROCESSING] Running tool selection audit across {len(TEST_SUITE)} evaluation nodes...")
    audit_results = []

    for item in TEST_SUITE:
        print(f" -> Testing Node #{item['id']}: '{item['question'][:40]}...'")
        
        messages = [
            {"role": "system", "content": "You are a helpful health insurance coordinator. Route the user request to appropriate tools when necessary."},
            {"role": "user", "content": item["question"]}
        ]

        try:
            # Query Groq to analyze model routing intent
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                tools=TOOLS_SCHEMAS,
                tool_choice="auto",
                temperature=0.0
            )
            
            tool_calls = response.choices[0].message.tool_calls
            
            # Analyze what tool was selected by the model
            if tool_calls:
                selected_tools = [call.function.name for call in tool_calls]
                actual_selection = " + ".join(selected_tools)
                args_captured = [json.loads(call.function.arguments) for call in tool_calls]
            else:
                actual_selection = "NONE"
                args_captured = "N/A"

            # Confirm match verification
            if item["expected_tool"] == "NONE (Conversational Fallback)" and actual_selection == "NONE":
                status = "✅ PASSED"
            elif "MULTIPLE" in item["expected_tool"] and tool_calls and len(tool_calls) > 1:
                status = "✅ PASSED"
            elif item["expected_tool"] in actual_selection:
                status = "✅ PASSED"
            else:
                status = "❌ MISMATCH"

        except Exception as e:
            actual_selection = f"ERROR: {str(e)}"
            args_captured = "N/A"
            status = "❌ FAILED"

        audit_results.append({
            "id": item["id"],
            "question": item["question"],
            "expected": item["expected_tool"],
            "actual": actual_selection,
            "args": json.dumps(args_captured),
            "status": status
        })

    # ---------------------------------------------------------
    # WRITE SYSTEM DETERMINATION MATRICES TO TOOL_CALL_LOG.MD
    # ---------------------------------------------------------
    print(f"[PROCESSING] Appending selection log report directly to: {output_md_path}")
    with open(output_md_path, "a", encoding="utf-8") as out:
        out.write("\n\n---\n## 🎯 Automated Tool Selection Verification Matrix\n\n")
        out.write(f"**Execution Audit Timestamp:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`\n")
        out.write("**Routing Engine model:** Cloud `llama-3.1-8b-instant` via Groq LPU\n\n")
        out.write("| Test Case | Input Question Text | Expected Tool Intent | Actual Selected Tool | Parameters Captured | Status |\n")
        out.write("| :---: | :--- | :--- | :--- | :--- | :---: |\n")
        
        for r in audit_results:
            out.write(f"| #{r['id']} | {r['question']} | {r['expected']} | `{r['actual']}` | `{r['args']}` | {r['status']} |\n")

    print("[SUCCESS] Selection validation suite run complete! Check tool_call_log.md for updates.")

if __name__ == "__main__":
    execute_tool_selection_audit()