import streamlit as st

from core.rag import get_langchain_history

from services.chat_service import save_current_chat

from utils.constants import (
    MEMORY_WINDOW,
    QUICK_QUESTIONS,
)


def _stream_response(rag_chain, question, chat_history):
    """Stream tokens from the RAG chain and return the full response."""

    lc_history = get_langchain_history(chat_history)

    full_response = ""

    # st.write_stream consumes a generator of str chunks
    def _token_generator():
        nonlocal full_response
        for chunk in rag_chain.stream({
            "question": question,
            "chat_history": lc_history,
        }):
            full_response += chunk
            yield chunk

    st.write_stream(_token_generator())

    return full_response


def render_chat_ui():

    st.subheader("💬 Chat with this Video")
    st.caption(
        "Responses are grounded strictly in transcript context."
    )

    # ── quick-question buttons ────────────────────────────
    cols = st.columns(3)

    for idx, question in enumerate(QUICK_QUESTIONS):

        if cols[idx % 3].button(
            question,
            key=f"quick_{idx}",
            use_container_width=True,
        ):
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

            if (
                total_turns > MEMORY_WINDOW
                and idx < total_turns - MEMORY_WINDOW
            ):
                st.caption("⚠️ Outside active memory window.")

    # ── chat input ────────────────────────────────────────
    user_question = st.chat_input("Ask about this video…")

    if st.session_state.get("pending_question"):
        user_question = st.session_state.pending_question
        st.session_state.pending_question = None

    if user_question:

        with st.chat_message("user"):
            st.write(user_question)

        with st.chat_message("assistant"):

            try:

                recent_history = st.session_state.chat_history[-MEMORY_WINDOW:]

                response = _stream_response(
                    rag_chain=st.session_state.rag_chain,
                    question=user_question,
                    chat_history=recent_history,
                )

                st.session_state.chat_history.append({
                    "user": user_question,
                    "ai": response,
                })

                save_current_chat(st.session_state.chat_history)

            except Exception as error:

                st.error("❌ Failed to generate response.")

                with st.expander("Error Details"):
                    st.code(str(error), language="text")

    # ── action buttons ────────────────────────────────────
    if st.session_state.chat_history:

        st.divider()

        col1, col2 = st.columns(2)

        if col1.button(
            "🗑️ Clear Chat",
            use_container_width=True,
        ):
            st.session_state.chat_history = []
            save_current_chat([])
            st.rerun()

        export_lines = []

        for idx, turn in enumerate(
            st.session_state.chat_history, 1
        ):
            export_lines.append(
                f"Turn {idx}\n\n"
                f"You: {turn['user']}\n\n"
                f"AI: {turn['ai']}\n\n"
            )

        col2.download_button(
            label="⬇️ Export Chat",
            data="\n".join(export_lines),
            file_name="chat_history.txt",
            mime="text/plain",
            use_container_width=True,
        )