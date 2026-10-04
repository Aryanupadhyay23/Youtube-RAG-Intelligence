import streamlit as st
from frontend.utils.constants import MEMORY_WINDOW, QUICK_QUESTIONS
from frontend.services.api_client import stream_chat
from frontend.services.chat_storage import save_current_chat


def render_chat_ui():
    """Render RAG Chat interface with streaming responses and history controls."""
    st.subheader("💬 Chat with Video")

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
        with st.chat_message("user"):
            st.write(turn["user"])
        with st.chat_message("assistant"):
            st.write(turn["ai"])

        if total_turns > MEMORY_WINDOW and idx < total_turns - MEMORY_WINDOW:
            st.caption("⚠️ Outside active memory window.")

    # Chat Input Box
    if st.session_state.get("pending_question"):
        user_question = st.session_state.pending_question
        st.session_state.pending_question = None
    else:
        user_question = st.chat_input("Ask about this video…")

    if user_question:
        with st.chat_message("user"):
            st.write(user_question)

        with st.chat_message("assistant"):
            status_box = st.empty()
            response_box = st.empty()
            full_response = ""

            try:
                # Stream responses from backend API
                for event in stream_chat(
                    video_id=st.session_state.get("video_id", ""),
                    chat_id=st.session_state.get("current_chat_id", "default_chat"),
                    query=user_question,
                    chat_history=chat_history[-MEMORY_WINDOW:],
                ):
                    event_type = event["type"]
                    value = event["value"]

                    if event_type == "status":
                        status_box.caption(f"⚙️ {value}...")
                    elif event_type == "token":
                        full_response += value
                        response_box.markdown(full_response + "▌")
                    elif event_type == "error":
                        status_box.error(f"❌ {value}")

                # Final token output without cursor
                if full_response:
                    response_box.markdown(full_response)
                    status_box.empty()

                    # Save turn
                    chat_history.append({"user": user_question, "ai": full_response})
                    save_current_chat(chat_history)

            except Exception as e:
                st.error(f"Error generating answer: {e}")

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
