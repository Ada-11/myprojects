# Rich UI Components Layout Verification Document

**Target Port Ingress Layer:** `http://localhost:8501`  
**Validation Engine Enforcement Layer:** Pydantic Structuring Controls  

---

## 📋 Visual Card Audit Matrix Checklist

- [x] **Test Case Node #1: Policy Citations Verification**  
  * **Input Query String dispatched:** `"Show me my plan document references."`  
  * **UI Structural Render:** The streaming engine skips tool-calling card flags but returns valid metadata source chunk arrays. The frontend renders an expandable text container labeled **"🔍 Policy sources used for context grounding"** right below the chat bubble. Clicking it opens a clean tray revealing the isolated document fragment IDs (`CHK-E9A3`, etc.) to prove the context source trace.  

- [x] **Test Case Node #2: Claim Status Card Verification**  
  * **Input Query String dispatched:** `"What is the current status of claim CLM9901?"`  
  * **UI Structural Render:** The backend matches the keyword "claim" and appends a `claim` data packet to the tail of the stream. The frontend catches the payload, validates it against the strict `ClaimStatusCard` Pydantic model contract, and maps the components to a bordered container featuring a distinct status metric header: `🟢 PAID`.  

- [x] **Test Case Node #3: Coverage Summary Card Verification**  
  * **Input Query String dispatched:** `"Is outpatient physical therapy covered under the Gold PPO plan?"`  
  * **UI Structural Render:** The backend interceptor catches the keyword "plan" and streams down a `coverage` payload packet. The frontend runs it through the `CoverageSummaryCard` schema parameters and draws a visual metrics card displaying a bold indicator tag stamp: `✅ APPROVED COVERAGE`.  
