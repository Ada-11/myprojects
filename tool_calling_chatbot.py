import os
import sys
import json
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ValidationError
from groq import Groq

# ---------------------------------------------------------
# 1. PYDANTIC OUTPUT DATA SCHEMAS FOR STRICT VALIDATION
# ---------------------------------------------------------
class CoverageValidationModel(BaseModel):
    plan_id: str = Field(..., min_length=2)
    procedure: str = Field(..., min_length=3)
    is_covered: bool
    limitations: str
    pre_authorization_required: bool

class ClaimStatusValidationModel(BaseModel):
    claim_id: str = Field(..., min_length=4)
    status: str = Field(..., pattern="^(paid|denied|pending_review)$")
    submitted_amount: float = Field(..., ge=0.0)
    allowed_amount: Optional[float] = Field(None, ge=0.0)
    member_responsibility: Optional[float] = Field(None, ge=0.0)
    insurance_paid: Optional[float] = Field(None, ge=0.0)
    denial_reason: Optional[str] = None

class PlanDetailsValidationModel(BaseModel):
    plan_id: str = Field(..., min_length=2)
    plan_name: str
    monthly_premium: float = Field(..., ge=0.0)
    annual_deductible: float = Field(..., ge=0.0)
    copay_pct: int = Field(..., ge=0, le=100)
    out_of_pocket_maximum: float = Field(..., ge=0.0)
    network_tier: str

class OutOfPocketValidationModel(BaseModel):
    procedure: str
    plan_id: str
    average_allowed_cost: float = Field(..., ge=0.0)
    estimated_member_deductible_impact: float = Field(..., ge=0.0)
    estimated_coinsurance_payment: float = Field(..., ge=0.0)
    total_estimated_out_of_pocket: float = Field(..., ge=0.0)

# ---------------------------------------------------------
# 2. MOCK DATASETS
# ---------------------------------------------------------
MOCK_COVERAGE = [
    {"plan_id": "P101", "procedure": "physical therapy", "is_covered": True, "limitations": "Covered up to 20 visits per calendar year.", "pre_authorization_required": False},
    {"plan_id": "P102", "procedure": "acupuncture", "is_covered": False, "limitations": "Explicitly categorized under plan policy exclusions.", "pre_authorization_required": False},
    {"plan_id": "P101", "procedure": "mri scan", "is_covered": True, "limitations": "Subject to annual deductible constraints.", "pre_authorization_required": True}
]

MOCK_CLAIMS = [
    {"claim_id": "CLM9901", "status": "paid", "submitted_amount": 450.00, "allowed_amount": 350.00, "member_responsibility": 35.00, "insurance_paid": 315.00, "denial_reason": None},
    {"claim_id": "CLM9902", "status": "denied", "submitted_amount": 1200.00, "allowed_amount": 0.00, "member_responsibility": 1200.00, "insurance_paid": 0.00, "denial_reason": "Missing required pre-authorization reference code."},
    {"claim_id": "CLM9903", "status": "pending_review", "submitted_amount": 150.00, "allowed_amount": None, "member_responsibility": None, "insurance_paid": None, "denial_reason": None}
]

MOCK_PLANS = [
    {"plan_id": "P101", "plan_name": "Gold PPO", "monthly_premium": 500.00, "annual_deductible": 2000.00, "copay_pct": 10, "out_of_pocket_maximum": 4000.00, "network_tier": "GOLD"},
    {"plan_id": "P102", "plan_name": "Silver HMO", "monthly_premium": 300.00, "annual_deductible": 1500.00, "copay_pct": 20, "out_of_pocket_maximum": 5500.00, "network_tier": "SILVER"},
    {"plan_id": "P103", "plan_name": "Bronze HMO", "monthly_premium": 150.00, "annual_deductible": 1000.00, "copay_pct": 30, "out_of_pocket_maximum": 7000.00, "network_tier": "BRONZE"}
]

MOCK_OUT_OF_POCKET = [
    {"procedure": "knee surgery", "plan_id": "P101", "average_allowed_cost": 5000.00, "estimated_member_deductible_impact": 2000.00, "estimated_coinsurance_payment": 300.00, "total_estimated_out_of_pocket": 2300.00},
    {"procedure": "routine evaluation", "plan_id": "P102", "average_allowed_cost": 150.00, "estimated_member_deductible_impact": 0.00, "estimated_coinsurance_payment": 30.00, "total_estimated_out_of_pocket": 30.00}
]

# ---------------------------------------------------------
# 3. PYTHON REALIZATION FUNCTIONS WITH INLINE PYDANTIC VALIDATION
# ---------------------------------------------------------
def check_coverage(plan_id: str, procedure: str) -> str:
    p_clean = procedure.strip().lower()
    raw_match = None
    for item in MOCK_COVERAGE:
        if item["plan_id"].upper() == plan_id.strip().upper() and item["procedure"] == p_clean:
            raw_match = item
            break
            
    if not raw_match:
        raw_match = {"plan_id": plan_id, "procedure": procedure, "is_covered": False, "limitations": "No record found.", "pre_authorization_required": False}
        
    try:
        # TEACHER INSTRUCTION COMPLIANCE: Instantiate Pydantic structural data parser validation block
        validated_data = CoverageValidationModel(**raw_match)
        return validated_data.model_dump_json()
    except ValidationError as ve:
        return json.dumps({"error": "Pydantic structural serialization failure.", "details": ve.errors()})

def get_claim_status(claim_id: str) -> str:
    raw_match = None
    for item in MOCK_CLAIMS:
        if item["claim_id"].upper() == claim_id.strip().upper():
            raw_match = item
            break
            
    if not raw_match:
        return json.dumps({"error": "Claim record matching target string could not be verified."})
        
    try:
        validated_data = ClaimStatusValidationModel(**raw_match)
        return validated_data.model_dump_json()
    except ValidationError as ve:
        return json.dumps({"error": "Pydantic data validation crash.", "details": ve.errors()})

def get_plan_details(plan_id: str) -> str:
    raw_match = None
    for item in MOCK_PLANS:
        if item["plan_id"].upper() == plan_id.strip().upper():
            raw_match = item
            break
            
    if not raw_match:
        return json.dumps({"error": "Invalid plan ID tracking descriptor metadata."})
        
    try:
        validated_data = PlanDetailsValidationModel(**raw_match)
        return validated_data.model_dump_json()
    except ValidationError as ve:
        return json.dumps({"error": "Pydantic data validation crash.", "details": ve.errors()})

def estimate_out_of_pocket_cost(procedure: str, plan_id: str) -> str:
    p_clean = procedure.strip().lower()
    raw_match = None
    for item in MOCK_OUT_OF_POCKET:
        if item["plan_id"].upper() == plan_id.strip().upper() and item["procedure"] == p_clean:
            raw_match = item
            break
            
    if not raw_match:
        return json.dumps({"error": "Custom out-of-pocket projection details unavailable."})
        
    try:
        validated_data = OutOfPocketValidationModel(**raw_match)
        return validated_data.model_dump_json()
    except ValidationError as ve:
        return json.dumps({"error": "Pydantic data validation crash.", "details": ve.errors()})

# ---------------------------------------------------------
# 4. SCHEMAS FOR GROQ TOOLS ARRAY PARAMETERS
# ---------------------------------------------------------
TOOLS_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_coverage",
            "description": "Checks if a specific medical procedure or treatment is covered under a member's insurance plan ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The insurance plan ID (e.g., 'P101', 'P102')."},
                    "procedure": {"type": "string", "description": "The medical procedure name (e.g., 'physical therapy')."}
                },
                "required": ["plan_id", "procedure"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_claim_status",
            "description": "Retrieves the current processing state, adjudication status, and payment breakdown for a submitted insurance claim ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "The unique alphanumeric string identifying the submitted medical claim (e.g., 'CLM9901')."}
                },
                "required": ["claim_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_plan_details",
            "description": "Retrieves core cost-sharing metrics, monthly premiums, and deductible tracking totals for an insurance plan ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The primary alphanumeric tracking ID of the targeted insurance tier."}
                },
                "required": ["plan_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_out_of_pocket_cost",
            "description": "Calculates an estimated member cost summary for a procedure based on a plan's specific coinsurance, deductible, and historical reference rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "procedure": {"type": "string", "description": "The medical treatment or service name to evaluate (e.g., 'knee surgery')."},
                    "plan_id": {"type": "string", "description": "The active insurance plan ID to execute calculation metrics against."}
                },
                "required": ["procedure", "plan_id"]
            }
        }
    }
]

# ---------------------------------------------------------
# 5. AGENT INTERACTIVE RUNTIME MULTI-TURN PIPELINE LOOP
# ---------------------------------------------------------
def run_agent_loop(user_query: str):
    api_key_env = os.environ.get("GROQ_API_KEY")
    if not api_key_env:
        print("[ERROR] GROQ_API_KEY environment variable not set. Run 'export GROQ_API_KEY=...' first.")
        return

    client = Groq(api_key=api_key_env)
    output_md_path = "/Users/ada/myprojects/my-first-app/tool_call_log.md"

    system_prompt = (
        "You are an advanced health insurance navigation assistant combining structural compliance limits with an accessible, professional tone.\n"
        "1. ACCURATE AND EMPATHETIC BALANCE: State all tool-returned metrics, deductibles, and coverage statuses with literal precision.\n"
        "2. MEDICAL DEFLECTION GUARDRAIL: If the user mentions health symptoms, state clearly that you cannot evaluate conditions and direct them to their doctor.\n"
        "3. OUT-OF-BOUNDS FALLBACK: If the tools don't return meaningful data, state: 'I don't know. The requested policy data is not present within your plan files.'\n"
        "4. STANDARD CLOSING DISCLAIMER: Conclude with this exact standalone paragraph: 'This is a structural coverage determination based on exact policy terms. This is not medical advice.'"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    print(f"\n[USER QUERY]: \"{user_query}\"")
    print("[PROCESSING] Querying Groq cloud with tool parameters...")

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        tools=TOOLS_SCHEMAS,
        tool_choice="auto",
        temperature=0.0
    )

    # FIXED: Added [0] index array accessor layout resolution matching updated SDK specifications
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        print(f"[AGENT STATE] Found {len(tool_calls)} functional call dependencies. Executing validation gates...")
        messages.append(response_message)

        available_functions = {
            "check_coverage": check_coverage,
            "get_claim_status": get_claim_status,
            "get_plan_details": get_plan_details,
            "estimate_out_of_pocket_cost": estimate_out_of_pocket_cost
        }

        # Open your verification document file using append mode to log audit trails
        with open(output_md_path, "a", encoding="utf-8") as out:
            out.write("\n\n### 📜 Live Agent Execution Transaction Log\n")
            out.write(f"*   **Timestamp:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`\n")
            out.write(f"*   **User Incoming Request Query:** \"{user_query}\"\n\n")
            out.write("| Executed Tool | Extracted Input Arguments | Pydantic Validated Result Output |\n")
            out.write("| :--- | :--- | :--- |\n")

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f" -> Routing to: `{function_name}()` | Arguments: {function_args}")
                
                # Execute Python function call path matching the target configuration string
                function_to_call = available_functions[function_name]
                validated_json_string = function_to_call(**function_args)
                
                print(f"    [PYDANTIC SECURE OUTPUT]: {validated_json_string}")

                # Append clean structural log data rows straight to your verification document
                clean_args = json.dumps(function_args)
                clean_result = validated_json_string.replace("\n", " ").strip()
                out.write(f"| `{function_name}` | `{clean_args}` | `{clean_result}` |\n")

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": validated_json_string
                })

        print("[PROCESSING] Forwarding validated data payload back to LPU gateway for response packaging...")
        final_response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.0
        )
        
        # FIXED: Added [0] index array accessor mapping profile here too
        final_answer = final_response.choices[0].message.content.strip()
        
        # Append the final assistant response string block to the audit trail log file
        with open(output_md_path, "a", encoding="utf-8") as out:
            out.write(f"\n**Final Natural-Language Agent Output Response:**\n```text\n{final_answer}\n```\n")
            out.write("-" * 80 + "\n")

        print("\n================ FINAL AGENT RESPONSE ================")
        print(final_answer)
        print("======================================================\n")
    else:
        print("\n================ FINAL AGENT RESPONSE ================")
        print(response_message.content.strip())
        print("======================================================\n")

if __name__ == "__main__":
    # Test Case 1: Triggers get_claim_status and appends verification log matrix
    run_agent_loop("What is the current status of claim CLM9901?")
    
    # Test Case 2: Triggers estimate_out_of_pocket_cost and logs audit trails
    run_agent_loop("Can you estimate my out of pocket cost for knee surgery under plan P101?")