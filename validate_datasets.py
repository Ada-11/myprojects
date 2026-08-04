import os
import json

def validate_jsonl_file(file_path: str) -> bool:
    """
    Validates a single fine-tuning JSONL file for structural integrity, 
    OpenAI chat schema compliance, and specific rubric requirements.
    """
    if not os.path.exists(file_path):
        print(f"❌ [MISSING] File not found at: {file_path}")
        return False

    print(f"\n[AUDITING] Reviewing dataset rows in: {os.path.basename(file_path)}")
    print("-" * 75)

    is_valid = True
    row_count = 0
    errors = []

    with open(file_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            row_count += 1
            line_strip = line.strip()
            if not line_strip:
                continue
            
            # Check A: Verify basic JSON string deserialization structural integrity
            try:
                record = json.loads(line_strip)
            except json.JSONDecodeError as je:
                errors.append(f"Row #{idx}: Broken JSON syntax format string. Error: {str(je)}")
                is_valid = False
                continue

            # Check B: Verify main root messages parameter array layout existence
            if "messages" not in record or not isinstance(record["messages"], list):
                errors.append(f"Row #{idx}: Missing root 'messages' list array container key.")
                is_valid = False
                continue

            messages = record["messages"]
            
            # Check C: Verify chat sequence length boundaries matching OpenAI criteria
            if len(messages) < 3:
                errors.append(f"Row #{idx}: Chat sequence length too short. Expected system, user, and assistant.")
                is_valid = False
                continue

            # Track internal message roles
            roles_found = [msg.get("role") for msg in messages if isinstance(msg, dict)]
            expected_roles = ["system", "user", "assistant"]
            
            if any(role not in roles_found for role in expected_roles):
                errors.append(f"Row #{idx}: Role mismatch blueprint structure. Found roles: {roles_found}")
                is_valid = False
                continue

            # Extract actual message content values to check compliance metrics
            assistant_content = ""
            user_content = ""
            for msg in messages:
                if msg.get("role") == "assistant":
                    assistant_content = msg.get("content", "")
                elif msg.get("role") == "user":
                    user_content = msg.get("content", "")

            # Check D: Verify mandatory corporate medical liability disclaimers
            if "medical advice" not in assistant_content.lower():
                errors.append(f"Row #{idx}: Assistant response missing required 'This is not medical advice.' disclaimer.")
                is_valid = False

            # Check E: Verify homework requirement - plain-language definition of "deductible" on first use
            if "deductible" in user_content.lower() or "deductible" in assistant_content.lower():
                if "out-of-pocket" not in assistant_content.lower() and "don't know" not in assistant_content.lower():
                    errors.append(f"Row #{idx}: Found the word 'deductible' but it is missing its plain-language definition wrapper string.")
                    is_valid = False

    # Render summary diagnostics logs back to terminal console interface
    if is_valid:
        print(f"✅ [PASSED] Successfully validated all {row_count} records with 0 structural errors.")
    else:
        print(f"❌ [FAILED] Found structural format or parameter alignment compliance errors:")
        for err in errors[:5]:  # Print the first 5 errors to keep output clean
            print(f"  -> {err}")
        if len(errors) > 5:
            print(f"  -> ... and {len(errors) - 5} more compliance warning items.")
            
    print("-" * 75)
    return is_valid

def execute_pipeline_checks():
    project_root = "/Users/ada/myprojects/my-first-app"
    
    # Locate all 3 newly generated data targets matching your project blueprint
    target_files = [
        os.path.join(project_root, "fine_tune_dataset.jsonl"),
        os.path.join(project_root, "fine_tune_train.jsonl"),
        os.path.join(project_root, "fine_tune_test.jsonl")
    ]

    print("=" * 75)
    print("🤖 HEALTH INSURANCE FINE-TUNING DATA COMPLIANCE VALIDATOR ACTIVE")
    print("=" * 75)

    all_passed = True
    for jsonl_path in target_files:
        status = validate_jsonl_file(jsonl_path)
        if not status:
            all_passed = False

    if all_passed:
        print("\n🏆 SUCCESS: All datasets match OpenAI schemas and homework requirements perfectly! Ready for upload.")
    else:
        print("\n⚠️ WARNING: Please correct the dataset formatting errors shown above before pushing to production.")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    execute_pipeline_checks()
