import os
import json
import uuid
import requests
import pandas as pd
import streamlit as st

# System configurations
BACKEND_URL = "http://localhost:8000/chat"
PLANS_CSV_PATH = "./data/plans.csv"

# Initialize persistent session variables
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR CONFIGURATION CONTROLS ---
with st.sidebar:
    st.markdown("## ⚙️ Account Parameters")
    plan_options = ["P101", "P102", "P103"]
    if os.path.exists(PLANS_CSV_PATH):
        try:
            df_plans = pd.read_csv(PLANS_CSV_PATH)
            if "plan_id" in df_plans.columns:
                plan_options = df_plans["plan_id"].dropna().unique().tolist()
        except Exception:
            pass

    selected_plan_id = st.selectbox("Active Insurance Policy Tier:", options=plan_options, index=0)
    st.markdown("---")
    if st.button("🔄 New conversation", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

st.title("💬 Insurance Member Navigation Hub")
st.caption(f"Currently inspecting rules for policy tier context: **{selected_plan_id}**")

# Render conversation thread history across reruns
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- CHAT INPUT STREAM ORCHESTRATION ---
if user_message := st.chat_input("Ask a policy question..."):
    
    # Render user prompt bubble on screen instantly
    with st.chat_message("user"):
        st.markdown(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})
    
    # Process incoming real-time stream layers
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        accumulated_text = ""
        
        # Display pre-first-token loading spinner indicator status immediately
        response_placeholder.markdown("⏳ *Consulting policy network layers... Fetching first token chunk...*")
        
        payload = {
            "session_id": st.session_state.session_id,
            "member_id": str(selected_plan_id),
            "message": user_message
        }
        
        try:
            # 1. TIMEOUT IMPLEMENTATION: Connect within 5s, enforce a strict read/chunk timeout of 15s
            response = requests.post(BACKEND_URL, json=payload, stream=True, timeout=(5.0, 15.0))
            
            if response.status_code == 200:
                # 2. SHIELDED CHUNK ITERATION LOOP
                line_iterator = response.iter_lines()
                
                while True:
                    try:
                        line = next(line_iterator, None)
                        if line is None:
                            break  # Stream closed naturally
                            
                        line_str = line.decode("utf-8").strip()
                        if not line_str:
                            continue

                        # FIXED: Split compound multi-packet buffers to intercept compressed token rows
                        sse_packets = line_str.split("\n\n")
                        for packet in sse_packets:
                            packet = packet.strip()
                            if packet.startswith("data:"):
                                raw_json = packet[5:].strip()
                                try:
                                    data_chunk = json.loads(raw_json)
                                    
                                    if "error" in data_chunk:
                                        accumulated_text += f"\n\n❌ **Stream Error:** {data_chunk['error']}"
                                        break
                                        
                                    token = data_chunk.get("token", "")
                                    accumulated_text += token
                                    # Append the typing cursor
                                    response_placeholder.markdown(accumulated_text + "▌")
                                except json.JSONDecodeError:
                                    pass
                            
                    except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError):
                        # 3. MID-STREAM DROPPED CONNECTION EXCEPTION HANDLER
                        accumulated_text += "\n\n⚠️ **[CONNECTION LOST]** *The network stream connection disconnected unexpectedly mid-transit. Displaying partial response transcript above.*"
                        break
                    except StopIteration:
                        break
                
                # Render final response frame cleanly without the cursor character
                response_placeholder.markdown(accumulated_text if accumulated_text else "⚠️ *No tokens received.*")
                
            else:
                accumulated_text = f"⚠️ Backend communication failure. Server code status: {response.status_code}"
                response_placeholder.markdown(accumulated_text)
                
        except requests.exceptions.Timeout:
            # 4. EXPLICIT CONNECTION TIMEOUT EXCEPTION HANDLER
            accumulated_text = "❌ **Network Timeout:** *The insurance database gateway server failed to respond within the designated execution window. Please try again.*"
            response_placeholder.markdown(accumulated_text)
        except Exception as general_err:
            accumulated_text = f"❌ Network Connection Error: Could not stream tokens. Details: {str(general_err)}"
            response_placeholder.markdown(accumulated_text)
            
        # Append the final response text to history to persist across reruns
        if accumulated_text:
            st.session_state.messages.append({"role": "assistant", "content": accumulated_text})
