import streamlit as st
from frontend.utils.constants import MEMORY_WINDOW, QUICK_QUESTIONS
from frontend.services.api_client import stream_chat
from frontend.services.chat_storage import save_current_chat
from frontend.utils.timestamp import linkify_timestamps


def render_chat_ui():
    """Render RAG Chat interface with streaming responses and history controls."""
    st.subheader("💬 Chat with Video")

    video_id = st.session_state.get("video_id", "")

    # Quick question prompt chips
    st.caption("Suggested Questions:")
    chip_cols = st.columns(len(QUICK_QUESTIONS))
    for i, question in enumerate(QUICK_QUESTIONS):
        if chip_cols[i].button(question, key=f"quick_{i}", use_container_width=True):
            st.session_state.pending_question = question
            st.rerun()

    st.divider()

    # Render conversational turns
    chat_history = st.session_state.get("chat_history", [])
    total_turns = len(chat_history)

    for idx, turn in enumerate(chat_history):
        with st.chat_message("user", avatar="👤"):
            st.markdown(turn["user"])
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(linkify_timestamps(turn["ai"], video_id))

        if total_turns > MEMORY_WINDOW and idx < total_turns - MEMORY_WINDOW:
            st.caption("⚠️ Outside active memory window.")

    # Chat Input Box
    if st.session_state.get("pending_question"):
        user_question = st.session_state.pending_question
        st.session_state.pending_question = None
    else:
        user_question = st.chat_input("Ask about this video…")

    if user_question:
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_question)

        with st.chat_message("assistant", avatar="🤖"):
            status_box = st.empty()
            response_box = st.empty()
            full_response = ""

            try:
                video_id = st.session_state.get("video_id", "")
                chat_id = st.session_state.get("current_chat_id", "default_chat")

                if not video_id:
                    st.error("⚠️ No video loaded. Please load a video first.")
                    return

                # Stream responses from backend API
                has_error = False
                for event in stream_chat(
                    video_id=video_id,
                    chat_id=chat_id,
                    query=user_question,
                    chat_history=chat_history[-MEMORY_WINDOW:],
                ):
                    event_type = event["type"]
                    value = event["value"]

                    if event_type == "status":
                        node_name = value.replace("Starting node: ", "")
                        labels = {
                            "rewrite_query": "🔍 Understanding query intent...",
                            "hybrid_retrieve": "⚡ Searching video transcript & keywords...",
                            "evaluate_retrieval": "🎯 Grading context relevance...",
                            "correct_query": "🔄 Refining query for better matches...",
                            "web_search": "🌐 Searching the web for additional context...",
                            "generate_answer": "✍️ Synthesizing answer with timestamps...",
                        }
                        status_label = labels.get(node_name, f"⚙️ {value}...")
                        status_box.caption(status_label)
                    elif event_type == "token":
                        status_box.empty()
                        full_response += value
                        response_box.markdown(full_response + "▌")
                    elif event_type == "error":
                        status_box.empty()
                        has_error = True

                        # User-friendly error messages
                        error_val = str(value)
                        if "connect" in error_val.lower() or "Connection" in error_val:
                            st.error("🔌 Cannot reach the backend. Please ensure the server is running on port 8000.")
                        elif "timeout" in error_val.lower():
                            st.error("⏱️ The request timed out. Try again or simplify your question.")
                        else:
                            st.error(f"❌ {value}")

                # Final token output without cursor
                if full_response:
                    formatted_final = linkify_timestamps(full_response, video_id)
                    response_box.markdown(formatted_final)
                    status_box.empty()

                    # Save turn
                    chat_history.append({"user": user_question, "ai": full_response})
                    save_current_chat(chat_history)

                elif not has_error:
                    response_box.markdown("*No response was generated. Please try again.*")

            except Exception as e:
                error_str = str(e)
                if "connect" in error_str.lower():
                    st.error("🔌 Cannot reach the backend server. Is it running?")
                elif "timeout" in error_str.lower():
                    st.error("⏱️ Request timed out. Try again.")
                else:
                    st.error(f"❌ Error: {error_str}")

    # Action Buttons: Clear & Export
    if chat_history:
        st.divider()
        col1, col2 = st.columns(2)
        if col1.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            save_current_chat([])
            st.rerun()

        export_data = "\n".join(
            f"Turn {i}\n\nYou: {t['user']}\n\nAI: {t['ai']}\n"
            for i, t in enumerate(chat_history, 1)
        )
        col2.download_button(
            label="⬇️ Export Chat (.txt)",
            data=export_data,
            file_name="chat_history.txt",
            mime="text/plain",
            use_container_width=True,
        )
