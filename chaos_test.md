- [x] **Test Case Simulation #1: Hard System Unhandled Tool Crash (Renamed Function)**  
  * **How to trigger:** Renamed `get_claim_status` to `BROKEN_get_claim_status` inside `mcp_server.py`.
  * **Dispatched User Prompt:** `"What is the processing status of claim CLM9901?"`
  * **Observed System Behavior:**
    1. The Supervisor Router accurately classified the intent and routed the workflow to the `ClaimsSpecialist` node.
    2. The underlying MCP client attempted to execute the tool, and the protocol server returned a structural `"Unknown tool: 'get_claim_status'"` exception string.
    3. **Graceful LLM Synthesis Handling:** Instead of throwing a raw code stack trace or a generic 500 error, the specialist agent's LLM safely ingested the error text string.
    4. The model automatically formulated an intelligent, natural-language explanation of the system misconfiguration and contextually suggested clear customer service contact options to guide the member.
