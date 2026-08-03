# Health Insurance RAG Agent: Tool Calling Schemas & Mock Datasets

This document outlines the strict structural JSON schemas used by the Groq/Llama-3.1 model to perform native function calling, along with complete mock datasets for system verification.

---

## 🛠️ Tool 1: `check_coverage`

### 1. JSON Schema Definition
```json
{
  "name": "check_coverage",
  "description": "Checks if a specific medical procedure or treatment is covered under a member's insurance plan ID.",
  "parameters": {
    "type": "object",
    "properties": {
      "plan_id": {
        "type": "string",
        "description": "The alphanumeric identifier of the insurance plan (e.g., 'P101', 'P102')."
      },
      "procedure": {
        "type": "string",
        "description": "The name of the medical procedure, service, or treatment to verify (e.g., 'physical therapy', 'acupuncture')."
      }
    },
    "required": ["plan_id", "procedure"]
  }
}
```

### 2. Mock Verification Dataset
```json
[
  {
    "plan_id": "P101",
    "procedure": "physical therapy",
    "is_covered": true,
    "limitations": "Covered up to 20 visits per calendar year when medically necessary.",
    "pre_authorization_required": false
  },
  {
    "plan_id": "P102",
    "procedure": "acupuncture",
    "is_covered": false,
    "limitations": "Explicitly categorized under plan policy exclusions.",
    "pre_authorization_required": false
  },
  {
    "plan_id": "P101",
    "procedure": "mri scan",
    "is_covered": true,
    "limitations": "Subject to annual deductible constraints.",
    "pre_authorization_required": true
  }
]
```

---

## 🛠️ Tool 2: `get_claim_status`

### 1. JSON Schema Definition
```json
{
  "name": "get_claim_status",
  "description": "Retrieves the current processing state, adjudication status, and payment breakdown for a submitted insurance claim ID.",
  "parameters": {
    "type": "object",
    "properties": {
      "claim_id": {
        "type": "string",
        "description": "The unique alphanumeric string identifying the submitted medical claim (e.g., 'CLM9901')."
      }
    },
    "required": ["claim_id"]
  }
}
```

### 2. Mock Verification Dataset
```json
[
  {
    "claim_id": "CLM9901",
    "status": "paid",
    "submitted_amount": 450.00,
    "allowed_amount": 350.00,
    "member_responsibility": 35.00,
    "insurance_paid": 315.00,
    "adjudicated_at": "2026-07-15T14:22:00Z",
    "denial_reason": null
  },
  {
    "claim_id": "CLM9902",
    "status": "denied",
    "submitted_amount": 1200.00,
    "allowed_amount": 0.00,
    "member_responsibility": 1200.00,
    "insurance_paid": 0.00,
    "adjudicated_at": "2026-07-28T09:11:15Z",
    "denial_reason": "Missing required pre-authorization reference code."
  },
  {
    "claim_id": "CLM9903",
    "status": "pending_review",
    "submitted_amount": 150.00,
    "allowed_amount": null,
    "member_responsibility": null,
    "insurance_paid": null,
    "adjudicated_at": null,
    "denial_reason": null
  }
]
```

---

## 🛠️ Tool 3: `get_plan_details`

### 1. JSON Schema Definition
```json
{
  "name": "get_plan_details",
  "description": "Retrieves core cost-sharing metrics, monthly premiums, and deductible tracking totals for an insurance plan ID.",
  "parameters": {
    "type": "object",
    "properties": {
      "plan_id": {
        "type": "string",
        "description": "The primary alphanumeric tracking ID of the targeted insurance tier configuration."
      }
    },
    "required": ["plan_id"]
  }
}
```

### 2. Mock Verification Dataset
```json
[
  {
    "plan_id": "P101",
    "plan_name": "Gold PPO",
    "monthly_premium": 500.00,
    "annual_deductible": 2000.00,
    "copay_pct": 10,
    "out_of_pocket_maximum": 4000.00,
    "network_tier": "GOLD"
  },
  {
    "plan_id": "P102",
    "plan_name": "Silver HMO",
    "monthly_premium": 300.00,
    "annual_deductible": 1500.00,
    "copay_pct": 20,
    "out_of_pocket_maximum": 5500.00,
    "network_tier": "SILVER"
  },
  {
    "plan_id": "P103",
    "plan_name": "Bronze HMO",
    "monthly_premium": 150.00,
    "annual_deductible": 1000.00,
    "copay_pct": 30,
    "out_of_pocket_maximum": 7000.00,
    "network_tier": "BRONZE"
  }
]
```

---

## 🛠️ Tool 4: `estimate_out_of_pocket_cost`

### 1. JSON Schema Definition
```json
{
  "name": "estimate_out_of_pocket_cost",
  "description": "Calculates an estimated member cost summary for a procedure based on a plan's specific coinsurance, deductible, and historical reference rates.",
  "parameters": {
    "type": "object",
    "properties": {
      "procedure": {
        "type": "string",
        "description": "The medical treatment or service name to evaluate (e.g., 'knee surgery', 'routine evaluation')."
      },
      "plan_id": {
        "type": "string",
        "description": "The active insurance plan ID to execute calculation metrics against."
      }
    },
    "required": ["procedure", "plan_id"]
  }
}
```

### 2. Mock Verification Dataset
```json
[
  {
    "procedure": "knee surgery",
    "plan_id": "P101",
    "average_allowed_cost": 5000.00,
    "estimated_member_deductible_impact": 2000.00,
    "estimated_coinsurance_payment": 300.00,
    "total_estimated_out_of_pocket": 2300.00,
    "disclaimer": "This is an estimate based on standard baseline metrics. Actual provider rates vary."
  },
  {
    "procedure": "routine evaluation",
    "plan_id": "P102",
    "average_allowed_cost": 150.00,
    "estimated_member_deductible_impact": 0.00,
    "estimated_coinsurance_payment": 30.00,
    "total_estimated_out_of_pocket": 30.00,
    "disclaimer": "Preventative baseline checkups may qualify for zero cost-sharing under ACA rules."
  }
]
```

### 📜 Live Agent Execution Transaction Log
*   **Timestamp:** `2026-08-03T02:33:20Z`
*   **User Incoming Request Query:** "What is the current status of claim CLM9901?"

| Executed Tool | Extracted Input Arguments | Pydantic Validated Result Output |
| :--- | :--- | :--- |
| `get_claim_status` | `{"claim_id": "CLM9901"}` | `{"claim_id":"CLM9901","status":"paid","submitted_amount":450.0,"allowed_amount":350.0,"member_responsibility":35.0,"insurance_paid":315.0,"denial_reason":null}` |

**Final Natural-Language Agent Output Response:**
```text
The current status of claim CLM9901 is paid. The submitted amount was $450.00, and the allowed amount was $350.00. The member's responsibility was $35.00, and the insurance paid $315.00. There is no denial reason associated with this claim.

This is a structural coverage determination based on exact policy terms. This is not medical advice.
```
--------------------------------------------------------------------------------


### 📜 Live Agent Execution Transaction Log
*   **Timestamp:** `2026-08-03T02:33:20Z`
*   **User Incoming Request Query:** "Can you estimate my out of pocket cost for knee surgery under plan P101?"

| Executed Tool | Extracted Input Arguments | Pydantic Validated Result Output |
| :--- | :--- | :--- |
| `estimate_out_of_pocket_cost` | `{"plan_id": "P101", "procedure": "knee surgery"}` | `{"procedure":"knee surgery","plan_id":"P101","average_allowed_cost":5000.0,"estimated_member_deductible_impact":2000.0,"estimated_coinsurance_payment":300.0,"total_estimated_out_of_pocket":2300.0}` |

**Final Natural-Language Agent Output Response:**
```text
Based on the data, your estimated out-of-pocket cost for knee surgery under plan P101 would be $2,300. This includes a deductible impact of $2,000 and a coinsurance payment of $300.

This is a structural coverage determination based on exact policy terms. This is not medical advice.
```
--------------------------------------------------------------------------------



---
## 🎯 Automated Tool Selection Verification Matrix

**Execution Audit Timestamp:** `2026-08-03T02:43:49Z`
**Routing Engine model:** Cloud `llama-3.1-8b-instant` via Groq LPU

| Test Case | Input Question Text | Expected Tool Intent | Actual Selected Tool | Parameters Captured | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| #1 | Is physical therapy covered under my plan P101? | check_coverage | `check_coverage` | `[{"plan_id": "P101", "procedure": "physical therapy"}]` | ✅ PASSED |
| #2 | Can you check if my claim CLM9902 has been processed or paid yet? | get_claim_status | `get_claim_status` | `[{"claim_id": "CLM9902"}]` | ✅ PASSED |
| #3 | What is the annual deductible and monthly premium for plan P102? | get_plan_details | `get_plan_details` | `[{"plan_id": "P102"}]` | ✅ PASSED |
| #4 | How much will I pay out-of-pocket for knee surgery under my plan P101? | estimate_out_of_pocket_cost | `estimate_out_of_pocket_cost` | `[{"plan_id": "P101", "procedure": "knee surgery"}]` | ✅ PASSED |
| #5 | I want to look up my coverage for routine evaluations under plan P102 and also check the deductible details for plan P102. | MULTIPLE (check_coverage + get_plan_details) | `get_plan_details + check_coverage` | `[{"plan_id": "P102"}, {"plan_id": "P102", "procedure": "routine evaluations"}]` | ✅ PASSED |
| #6 | Hi, I am stressed about my medical bills. Can you tell me a joke to cheer me up? | NONE (Conversational Fallback) | `NONE` | `"N/A"` | ✅ PASSED |
