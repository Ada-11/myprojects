import os
import json
import uuid
import requests
import pandas as pd
import streamlit as st

# Import the structural Pydantic card schemas from your project module
from response_cards import ClaimStatusCard, CoverageSummaryCard

BACKEND_URL = "http://localhost:8000/chat"

st.set_page_config(page_title="Member Dashboard", layout="wide")

# ----------------------------------------------------------------------
# 1. REUSABLE UI CARD RENDERING PIPELINE BLOCKS (Moved to Top)
# ----------------------------------------------------------------------
def render_claim_status_card(card: ClaimStatusCard):
    """Renders a beautifully bounded micro-dashboard layout card for medical claims."""
    status_colors = {"paid": "🟢 PAID", "denied": "🔴 DENIED", "pending_review": "🟡 PENDING REVIEW"}
    display_status = status_colors.get(card.status.lower(), card.status.upper())
    
    with st.container(border=True):
        st.markdown(f"### 📄 Medical Claim Summary Details")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Claim Identification ID", value=card.claim_id)
        with col2:
            st.metric(label="Adjudication State", value=display_status)
        with col3:
            st.metric(label="Processed Financial Value", value=f"${card.amount:,.2f}")
        with col4:
            st.metric(label="Filing Operational Date", value=card.date)

def render_coverage_summary_card(card: CoverageSummaryCard):
    """Renders a structured cost-sharing profile matrix verification card."""
    display_covered = "✅ APPROVED COVERAGE" if card.covered else "❌ POLICY EXCLUSION"
    
    with st.container(border=True):
        st.markdown(f"### 🛡️ Policy Coverage Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Selected Plan Tier", value=card.plan_name)
        with col2:
            st.metric(label="Annual Tracking Deductible", value=f"${card.deductible:,.2f}")
        with col3:
            st.metric(label="Cost-Sharing Copay Rate", value=card.copay)
        with col4:
            st.metric(label="Policy Status Approval", value=display_covered)


# ----------------------------------------------------------------------
# 2. INITIALIZE PERSISTENT STATE VARIABLES
# ----------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("💬 Insurance Member Navigation Portal")

# ----------------------------------------------------------------------
# 3. RENDER CONVERSATION HISTORY (Now functions are defined safely)
# ----------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "content" in msg and msg["content"]:
            st.markdown(msg["content"])
        
        # Re-render embedded cards from history logs safely
        if "card_type" in msg and msg["card_type"]:
            if msg["card_type"] == "claim":
                render_claim_status_card(ClaimStatusCard(**msg["card_payload"]))
            elif msg["card_type"] == "coverage":
                render_coverage_summary_card(CoverageSummaryCard(**msg["card_payload"]))
                
        # Re-render citations from history logs cleanly
        if msg["role"] == "assistant" and msg.get("citations"):
            with st.expander("🔍 Policy sources used for context grounding"):
                for cid in msg["citations"]:
                    st.caption(f"📌 **Document Source Fragment ID:** `{cid}`")


# ----------------------------------------------------------------------
# 4. CHAT INPUT STREAM ORCHESTRATION LOOP
# ----------------------------------------------------------------------
if user_message := st.chat_input("Ask about a claim or coverage rules (e.g., 'What is status of claim CLM9901?')..."):
    
    with st.chat_message("user"):
        st.markdown(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})
    
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        accumulated_text = ""
        
        response_placeholder.markdown("⏳ *Consulting policy networks... Fetching real-time tokens...*")
        
        payload = {
            "session_id": st.session_state.session_id,
            "member_id": "P101",
            "message": user_message
        }
        
        final_citations = []
        detected_card_type = None
        detected_card_payload = None
        
        try:
            response = requests.post(BACKEND_URL, json=payload, stream=True, timeout=(5.0, 60.0))
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data:"):
                            raw_json = line_str[5:].strip()
                            try:
                                data_chunk = json.loads(raw_json)
                                
                                if "error" in data_chunk:
                                    st.error(f"Stream Error: {data_chunk['error']}")
                                    break
                                
                                if "token" in data_chunk:
                                    token = data_chunk.get("token", "")
                                    accumulated_text += token
                                    response_placeholder.markdown(accumulated_text + "▌")
                                
                                if "citations" in data_chunk:
                                    final_citations = data_chunk.get("citations", [])
                                    detected_card_type = data_chunk.get("card_type")
                                    detected_card_payload = data_chunk.get("card_payload")
                                    
                            except json.JSONDecodeError:
                                pass
                
                response_placeholder.markdown(accumulated_text if accumulated_text else "⚠️ *Stream processing complete.*")
                
                if detected_card_type == "claim" and detected_card_payload:
                    validated_claim = ClaimStatusCard(**detected_card_payload)
                    render_claim_status_card(validated_claim)
                elif detected_card_type == "coverage" and detected_card_payload:
                    validated_coverage = CoverageSummaryCard(**detected_card_payload)
                    render_coverage_summary_card(validated_coverage)
                    
                if final_citations:
                    with st.expander("🔍 Policy sources used for context grounding"):
                        for cid in final_citations:
                            st.caption(f"📌 **Document Source Fragment ID:** `{cid}`")
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": accumulated_text,
                    "citations": final_citations,
                    "card_type": detected_card_type,
                    "card_payload": detected_card_payload
                })
            else:
                st.error(f"Backend API error status code: {response.status_code}")
        except Exception as e:
            st.error(f"Failed to communicate with API server: {str(e)}")
