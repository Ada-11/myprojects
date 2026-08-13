import os
import sys
import json
import pandas as pd
from fastmcp import FastMCP

# Ensure the parent directory is accessible for local module lookups
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

# Import your Day 10 vector database retrieval pipeline logic safely
try:
    from retrieval_engine import retrieve
except ImportError:
    # Resilient fallback handler if structural imports are nested differently
    def retrieve(query: str) -> dict:
        return {"context_block": f"[MOCK CONTEXT] Grounded vector nodes matching query: '{query}'"}

# Initialize the customizable FastMCP server manager layout
mcp_server_app = FastMCP("InsurancePolicyServer")

# Configuration Paths matching Day 4 files properties
PLANS_CSV_PATH = os.path.join(CURRENT_DIR, "data", "plans.csv")

# ----------------------------------------------------------------------
# EXPOSE TOOL 1: POLICY COVERAGE ANALYSIS VIA THE MCP PROTOCOL
# ----------------------------------------------------------------------
@mcp_server_app.tool()
def check_coverage(plan_id: str, procedure: str) -> str:
    """
    Checks if a specific medical procedure or treatment is covered under a member's insurance plan ID.
    
    Use this tool whenever a member asks if an explicit treatment (like physical therapy, 
    acupuncture, or MRI scans) is approved, or if they need to check policy visit limits.

    Args:
        plan_id: The primary alphanumeric plan code string to evaluate (e.g., 'P101', 'P102', 'P103').
        procedure: The exact name of the medical procedure to inspect (e.g., 'physical therapy').
    """
    clean_procedure = procedure.strip().lower()
    clean_plan = plan_id.strip().upper()
    
    # 1. RUN DAY 10 VECTOR DATABASE LOOKUP TO GATHER GROUNDED CONTEXT
    vector_payload = retrieve(f"Is {clean_procedure} covered under plan {clean_plan}?")
    context_grounding_block = vector_payload.get("context_block", "")
    
    # 2. RUN DAY 4 STRUCTURAL PLANS CSV DATABASE MATRIX LOOKUP
    deductible_metric = 0.0
    copay_rate = "0%"
    plan_name_string = "Unknown Tier"
    
    if os.path.exists(PLANS_CSV_PATH):
        try:
            df_plans = pd.read_csv(PLANS_CSV_PATH)
            matched_row = df_plans[df_plans['plan_id'].astype(str).str.upper() == clean_plan]
            if not matched_row.empty:
                deductible_metric = float(matched_row['annual_deductible'].values[0])
                copay_rate = str(matched_row['copay_pct'].values[0]) + "%"
                plan_name_string = str(matched_row['plan_name'].values[0])
        except Exception:
            pass

    response_dictionary = {
        "requested_plan_id": clean_plan,
        "verified_plan_name": plan_name_string,
        "targeted_procedure": clean_procedure,
        "annual_deductible_impact": f"${deductible_metric:,.2f}",
        "member_copay_coinsurance_rate": copay_rate,
        "vector_grounded_notes": context_grounding_block if context_grounding_block else "No extraction found."
    }
    return json.dumps(response_dictionary, indent=2)

# ----------------------------------------------------------------------
# EXPOSE TOOL 2: CLAIMS RECORD STATUS LOOKUP VIA THE MCP PROTOCOL
# ----------------------------------------------------------------------
@mcp_server_app.tool()
def get_claim_status(claim_id: str) -> str:
    """
    Retrieves the current processing state, adjudication status, and payment breakdown for a submitted insurance claim ID.
    
    Use this tool whenever a member asks for updates on a specific claim number to see if it has been 
    paid, pending review, or denied under policy rules.

    Args:
        claim_id: The unique alphanumeric tracking identifier string for the submitted claim (e.g., 'CLM9901').
    """
    clean_claim = claim_id.strip().upper()
    
    mock_claims_db = {
        "CLM9901": {"status": "paid", "submitted": 450.00, "allowed": 350.00, "member_share": 35.00, "insurance_paid": 315.00, "denial_reason": None},
        "CLM9902": {"status": "denied", "submitted": 1200.00, "allowed": 0.00, "member_share": 1200.00, "insurance_paid": 0.00, "denial_reason": "Missing required pre-authorization reference code."},
        "CLM9903": {"status": "pending_review", "submitted": 150.00, "allowed": None, "member_share": None, "insurance_paid": None, "denial_reason": None}
    }
    
    record_match = mock_claims_db.get(clean_claim)
    if not record_match:
        return json.dumps({"error": f"Claim record matching tracking string '{clean_claim}' could not be verified in the ledger."})
        
    return json.dumps({
        "claim_identification_id": clean_claim,
        "adjudication_state_status": record_match["status"].upper(),
        "submitted_financial_amount": f"${record_match['submitted']:,.2f}",
        "allowed_financial_amount": f"${record_match['allowed']:,.2f}" if record_match["allowed"] else "Under Evaluation",
        "member_responsibility_balance": f"${record_match['member_share']:,.2f}" if record_match["member_share"] else "Under Evaluation",
        "insurance_company_payout": f"${record_match['insurance_paid']:,.2f}" if record_match["insurance_paid"] else "Under Evaluation",
        "system_denial_notes": record_match["denial_reason"]
    }, indent=2)

if __name__ == "__main__":
    mcp_server_app.run()
