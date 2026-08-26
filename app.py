import os
import json
import uuid
import requests
import pandas as pd
import streamlit as st

# CRITICAL: Must be the first command. Forced expanded to ensure visibility.
st.set_page_config(
    page_title="Orion Member Portal", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Import the structural Pydantic card schemas from your project module
from response_cards import ClaimStatusCard, CoverageSummaryCard

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/chat")

# ----------------------------------------------------------------------
# 0. CUSTOM STYLING (ORION THEME & SIDEBAR TOGGLE FIX)
# ----------------------------------------------------------------------
st.markdown("""
    <style>
        /* Make header transparent so sidebar toggle stays functional */
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0);
            color: #5C6BC0;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        
        /* Layout Padding */
        div.block-container {padding-top: 2rem;}

        /* Hero Landing Branding */
        .hero-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px 0px 10px 0px;
        }
        .orion-circle {
            width: 70px;
            height: 70px;
            border: 6px solid #5C6BC0;
            border-radius: 50%;
            margin-bottom: 15px;
        }
        .hero-title {
            font-family: 'Times New Roman', serif;
            font-size: 48px;
            font-weight: 400;
            color: #1A1A1A;
        }
        .disclaimer-text {
            text-align: center;
            font-size: 11px;
            color: #999;
            margin-top: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

# ----------------------------------------------------------------------
# 1. REUSABLE UI CARD RENDERING PIPELINE BLOCKS (FULL WIDTH)
# ----------------------------------------------------------------------
def render_claim_status_card(card: ClaimStatusCard):
    """Renders a full-width card with half-size headers and uniform text."""
    status_colors = {"paid": "🟢 Paid", "denied": "🔴 Denied", "pending_review": "🟡 Pending Review"}
    display_status = status_colors.get(card.status.lower(), card.status.title())
    
    with st.container(border=True):
        st.markdown(f"##### 📄 Medical Claim Summary Details")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Claim ID**")
            st.markdown(f"`{card.claim_id}`")
        with col2:
            st.markdown("**Adjudication State**")
            st.markdown(f"{display_status}")
        with col3:
            st.markdown("**Processed Value**")
            st.markdown(f"${card.amount:,.2f}")
        with col4:
            st.markdown("**Filing Date**")
            st.markdown(f"{card.date}")

def render_coverage_summary_card(card: CoverageSummaryCard):
    """Renders a full-width card with half-size headers and uniform text."""
    display_status_text = "Approved Coverage" if card.covered else "Policy Exclusion"
    display_icon = "✅" if card.covered else "❌"
    
    with st.container(border=True):
        st.markdown(f"##### 🛡️ Policy Coverage Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Plan Tier**")
            st.markdown(f"{card.plan_name}")
        with col2:
            st.markdown("**Annual Deductible**")
            st.markdown(f"${card.deductible:,.2f}")
        with col3:
            st.markdown("**Cost-Sharing Copay Rate**")
            st.markdown(f"{card.copay}")
        with col4:
            st.markdown("**Policy Status**")
            st.markdown(f"{display_icon} {display_status_text}")


# ----------------------------------------------------------------------
# 2. INITIALIZE PERSISTENT STATE VARIABLES (HISTORY PRESERVATION)
# ----------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- ORION SIDEBAR (OSCAR STYLE) ---
with st.sidebar:
    st.markdown("<h2 style='color: #5C6BC0; font-family: sans-serif; font-weight: bold;'>Orion</h2>", unsafe_allow_html=True)
    if st.button("+ New chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
    st.divider()
    st.caption("Policy navigation assistance active.")
    st.caption(f"Session Trace: `{st.session_state.session_id[:8]}`")

# ----------------------------------------------------------------------
# 3. RENDER CONVERSATION HISTORY & HERO
# ----------------------------------------------------------------------
if not st.session_state.messages:
    # HERO SECTION (MATCHING IMAGE)
    st.markdown("""
        <div class="hero-container">
            <div class="orion-circle"></div>
            <div class="hero-title">Ask Orion</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 25px;'>Your Health Insurance Policy Assistant</p>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🩺 Understanding symptoms", use_container_width=True):
            st.session_state.landing_query = "What coverage do I have for symptom evaluation?"
        if st.button("💰 Understand costs and benefits", use_container_width=True):
            st.session_state.landing_query = "Explain my plan's deductible and out-of-pocket costs."
    with c2:
        if st.button("💊 Learning about medications", use_container_width=True):
            st.session_state.landing_query = "Tell me about my prescription drug coverage."
        if st.button("🔍 Search for a provider", use_container_width=True):
            st.session_state.landing_query = "How do I find an in-network doctor?"

# Message history logic (Strict preservation)
for msg in st.session_state.messages:
    avatar = "🛡️" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        if "content" in msg and msg["content"]:
            st.markdown(msg["content"])
        
        if msg.get("card_type") and msg.get("card_payload"):
            try:
                if msg["card_type"] == "claim":
                    render_claim_status_card(ClaimStatusCard(**msg["card_payload"]))
                elif msg["card_type"] == "coverage":
                    render_coverage_summary_card(CoverageSummaryCard(**msg["card_payload"]))
            except Exception as e:
                st.error(f"Card Restore Error: {e}")
                
        if msg["role"] == "assistant" and msg.get("citations"):
            with st.expander("🔍 Policy Grounding"):
                for cid in msg["citations"]:
                    st.caption(f"📌 Source ID: `{cid}`")


# ----------------------------------------------------------------------
# 4. CHAT INPUT STREAM ORCHESTRATION LOOP (PRESERVING FUNCTIONALITY)
# ----------------------------------------------------------------------
if "landing_query" in st.session_state:
    user_message = st.session_state.pop("landing_query")
    trigger = True
else:
    user_message = st.chat_input("Ask Orion about a claim or coverage rules...")
    trigger = True if user_message else False

if trigger:
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})
    
    with st.chat_message("assistant", avatar="🛡️"):
        response_placeholder = st.empty()
        accumulated_text = ""
        response_placeholder.markdown("⏳ *Orion is consulting policy records...*")
        
        payload = {
            "session_id": st.session_state.session_id,
            "member_id": "P101",
            "message": user_message
        }
        
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
                                if "token" in data_chunk:
                                    accumulated_text += data_chunk.get("token", "")
                                    response_placeholder.markdown(accumulated_text + "▌")
                                if "card_type" in data_chunk:
                                    detected_card_type = data_chunk.get("card_type")
                                    detected_card_payload = data_chunk.get("card_payload")
                            except: pass
                
                response_placeholder.markdown(accumulated_text)
                
                if detected_card_type and detected_card_payload:
                    if detected_card_type == "claim":
                        render_claim_status_card(ClaimStatusCard(**detected_card_payload))
                    elif detected_card_type == "coverage":
                        render_coverage_summary_card(CoverageSummaryCard(**detected_card_payload))
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": accumulated_text,
                    "card_type": detected_card_type,
                    "card_payload": detected_card_payload
                })
                st.rerun() 
            else:
                st.error(f"Backend API error: {response.status_code}")
        except Exception as e:
            st.error(f"Connection failed: {str(e)}")

# Bottom disclaimer
if not st.session_state.messages:
    st.markdown("<p class='disclaimer-text'>Not a substitute for medical advice. In an emergency call 911.</p>", unsafe_allow_html=True)