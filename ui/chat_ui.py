import json
import requests
import streamlit as st

from services.chat_service import save_current_chat
from utils.constants import MEMORY_WINDOW, QUICK_QUESTIONS

def _stream_response(question, chat_history):
    """Invoke FastAPI backend and stream the Server-Sent Events."""
    
    payload = {
        "video_id": st.session_state.video_id,
        "chat_id": st.session_state.current_chat_id,
        "query": question,
        "chat_history": chat_history
    }
    
    status_placeholder = st.empty()
    response_placeholder = st.empty()
    
    full_response = ""
    event_type = None
    
    try:
        # Connect to FastAPI SSE endpoint
        with requests.post("http://localhost:8000/chat/stream", json=payload, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("event: "):
                        event_type = decoded_line[7:]
                    elif decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        if not data_str or data_str == "{}":
                            continue
                            
                        try:
                            data = json.loads(data_str)
                            if event_type == "status":
                                status_placeholder.caption(f"⚙️ {data.get('message', '')}...")
                            elif event_type == "token":
                                full_response += data.get("token", "")
                                response_placeholder.markdown(full_response + "▌")
                            elif event_type == "error":
                                status_placeholder.error(data.get("error", "Unknown error"))
                        except json.JSONDecodeError:
                            pass
    except requests.exceptions.ConnectionError:
        status_placeholder.error("❌ Could not connect to API server. Is Uvicorn running on port 8000?")
    except Exception as e:
        status_placeholder.error(f"❌ Error during API streaming: {str(e)}")
        
    # Final cleanup
    status_placeholder.empty()
    response_placeholder.markdown(full_response)
    
    return full_response

def render_chat_ui():
    st.subheader("💬 Chat with this Video")
    st.caption("Responses are grounded strictly in transcript context using Async Corrective RAG (via FastAPI).")

    # ── quick-question buttons ────────────────────────────
    cols = st.columns(3)
    for idx, question in enumerate(QUICK_QUESTIONS):
        if cols[idx % 3].button(question, key=f"quick_{idx}", use_container_width=True):
            st.session_state.pending_question = question
            
    st.divider()

    # ── chat history ──────────────────────────────────────
    if not st.session_state.chat_history:
        st.info("💡 Ask a question to begin.")
    else:
        total_turns = len(st.session_state.chat_history)
        for idx, turn in enumerate(st.session_state.chat_history):
            with st.chat_message("user"):
                st.write(turn["user"])
            with st.chat_message("assistant"):
                st.write(turn["ai"])
                
            if total_turns > MEMORY_WINDOW and idx < total_turns - MEMORY_WINDOW:
                st.caption("⚠️ Outside active memory window.")

    # ── chat input ────────────────────────────────────────
    if st.session_state.get("pending_question"):
        user_question = st.session_state.pending_question
        st.session_state.pending_question = None
    else:
        user_question = st.chat_input("Ask about this video…")

    if user_question:
        with st.chat_message("user"):
            st.write(user_question)

        with st.chat_message("assistant"):
            try:
                recent_history = st.session_state.chat_history[-MEMORY_WINDOW:]
                
                response = _stream_response(
                    question=user_question,
                    chat_history=recent_history,
                )

                st.session_state.chat_history.append({
                    "user": user_question,
                    "ai": response,
                })

                save_current_chat(st.session_state.chat_history)
            except Exception as error:
                st.warning("⚠️ Failed to generate response.")
                with st.expander("Error Details"):
                    st.code(str(error), language="text")

    # ── action buttons ────────────────────────────────────
    if st.session_state.chat_history:
        st.divider()
        col1, col2 = st.columns(2)
        if col1.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            save_current_chat([])
            st.rerun()

        export_lines = []
        for idx, turn in enumerate(st.session_state.chat_history, 1):
            export_lines.append(f"Turn {idx}\n\nYou: {turn['user']}\n\nAI: {turn['ai']}\n\n")

        col2.download_button(
            label="⬇️ Export Chat",
            data="\n".join(export_lines),
            file_name="chat_history.txt",
            mime="text/plain",
            use_container_width=True,
        )