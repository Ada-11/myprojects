# Real-Time Token Streaming Architecture & Operational Notes

**Project Subdirectory:** `/Users/ada/myprojects/my-first-app`  
**Protocol Layout:** Server-Sent Events (SSE) `text/event-stream`  

---

## 🏗️ Technical Pipeline Topology

The streaming pipeline operates as a decoupled, multi-tier asynchronous generator network:
1. **Frontend (`app.py`)**: Uses the `requests` library with `stream=True` to keep a long-lived HTTP port connection open on port 8000. It reads data line-by-line via a `while` chunk loop and prints text updates in place using `st.empty()`.
2. **Backend API (`main.py`)**: Converts the regular JSON REST handler route into an explicit `StreamingResponse` using a Python generator function loop.
3. **Core Model Layer (`tool_calling_chatbot.py`)**: Switches the underlying Groq cloud client completion invocation into native streaming mode (`stream=True`). It catches chunks off the cloud LPU chip array and wraps each token into an SSE payload string element: `data: {"token": "chunk"}\n\n`.

---

## 🔍 Pre-First-Token UX & Loading State Execution

Before the first token arrives at the frontend, the model must execute tool-calling parsing logic and query local databases, which causes an inevitable **0.2s to 0.5s network delay**.

To prevent the user interface from appearing frozen or broken during this pause, the system uses a **Pre-First-Token Loading State Tracker**:
* Immediate visual feedback is displayed on screen via `response_placeholder.markdown("⏳ *Consulting policy network layers...*")` the split second the query is sent.
* Once the first token clears the local network adapter port, the placeholder string is cleanly overwritten by the text completion, creating a smooth user experience.

---

## 🛡️ Mid-Stream Fault Tolerance & Exception Shielding

Network connections on distributed enterprise architectures are inherently fragile and subject to packet drops. The system handles connection drops through these mechanisms:

### 1. Connection & Read Timeout Guardrails
The frontend script replaces simple connection attempts with an explicit dual-stage parameter tuple constraint: `timeout=(5.0, 15.0)`.
* **5.0s Connect Timeout**: If the backend API container is down or completely unreachable, the network call aborts after 5 seconds instead of hanging endlessly.
* **15.0s Read/Chunk Timeout**: If the server completely stops sending data characters mid-stream for more than 15 seconds, the line iterator breaks and triggers a user-facing error notification.

### 2. Handling Mid-Stream Connection Drops
If a network cable is pulled or a proxy server terminates the connection while tokens are actively streaming, the application intercepts the resulting `ConnectionError` or `ChunkedEncodingError` inside a localized `try/except` loop block.

Instead of crashing the entire Streamlit page or losing data, the script:
* **Preserves Partial Transcripts**: Gracefully keeps all text tokens already captured on screen.
* **Appends a Warning Banner**: Appends an explicit inline notification alerting the member: `⚠️ [CONNECTION LOST] The network stream connection disconnected unexpectedly mid-transit. Displaying partial response transcript above.`
* **Saves State History**: Commits the partial response cleanly to `st.session_state` so the conversation history tracks properly across future page reruns.
