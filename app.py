import os
import uuid
import requests
import pandas as pd
import streamlit as st

# System configuration settings
BACKEND_URL = "http://localhost:8000/chat"
PLANS_CSV_PATH = "./data/plans.csv"

# 1. Generate session_id exactly once via uuid4 and store in session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# ----------------------------------------------------------------------
# SIDEBAR CONTROLS SECTION
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Account Parameters")
    
    # Extract plan options dynamically from your Day 4 plans table
    plan_options = ["P101", "P102", "P103"]  # Resilient fallback default options array
    if os.path.exists(PLANS_CSV_PATH):
        try:
            df_plans = pd.read_csv(PLANS_CSV_PATH)
            if "plan_id" in df_plans.columns:
                plan_options = df_plans["plan_id"].dropna().unique().tolist()
        except Exception:
            pass

    selected_plan_id = st.selectbox(
        "Active Insurance Policy Tier:",
        options=plan_options,
        index=0
    )
    
    st.markdown("---")
    
    # "New conversation" button that resets the session_id and clears history
    if st.button("🔄 New conversation", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption(f"**Tracking Key Session Vector:**\n`{st.session_state.session_id}`")

# ----------------------------------------------------------------------
# MAIN INTERACTIVE CHAT STREAM CANVAS RENDERING
# ----------------------------------------------------------------------
st.title("💬 Insurance Member Navigation Hub")
st.caption(f"Currently inspecting rules for policy tier context: **{selected_plan_id}**")

# Render the conversation thread history across Streamlit reruns
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Capture new user messages on each chat input submission turn
if user_message := st.chat_input("Ask a policy question..."):
    
    # Render user prompt bubble on screen instantly
    with st.chat_message("user"):
        st.markdown(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})
    
    # Render assistant helper layer while executing backend network calls
    with st.chat_message("assistant"):
        with st.spinner("Processing policy parameters..."):
            
            # Package parameters dynamically tracking selected sidebar member_id variables
            payload = {
                "session_id": st.session_state.session_id,
                "member_id": str(selected_plan_id),  
                "message": user_message
            }
            
            try:
                # POST to your /chat endpoint via requests module
                response = requests.post(BACKEND_URL, json=payload, timeout=30)
                
                if response.status_code == 200:
                    agent_answer = response.json().get("agent_response", "Error: Missing response parameters.")
                else:
                    agent_answer = f"⚠️ Backend API error encountered. Code: {response.status_code}"
            except Exception as e:
                agent_answer = f"❌ Network Connection Error: Could not reach port 8000. Error: {str(e)}"
            
            # Render the final text answer directly onto the interface canvas window
            st.markdown(agent_answer)
            st.session_state.messages.append({"role": "assistant", "content": agent_answer})
