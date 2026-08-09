# response_cards.py
from pydantic import BaseModel, Field

class ClaimStatusCard(BaseModel):
    """
    Structured UI schema contract enforcing format parameters 
    for insurance claim adjudication state outputs.
    """
    claim_id: str = Field(..., description="Unique alphanumeric identifier for the medical claim.")
    status: str = Field(..., description="Current processing state (e.g., paid, denied, pending_review).")
    amount: float = Field(..., description="The total financial value requested or processed for the claim.", ge=0.0)
    date: str = Field(..., description="ISO 8601 formatted date string indicating when the claim was filed.")

class CoverageSummaryCard(BaseModel):
    """
    Structured UI schema contract enforcing cost-sharing 
    and policy status details for plan verification components.
    """
    plan_name: str = Field(..., description="The marketing or tier name of the policy (e.g., Gold PPO, Silver HMO).")
    deductible: float = Field(..., description="The annual member out-of-pocket tracking deductible requirement.", ge=0.0)
    copay: str = Field(..., description="The flat fee or percentage cost-sharing metric required per service visit.")
    covered: bool = Field(..., description="Boolean flag stating if the referenced procedure type is approved under policy rules.")
