import streamlit as st

from services.chat_service import save_current_chat
from utils.constants import MEMORY_WINDOW, QUICK_QUESTIONS

def _stream_response(question, chat_history):
    """Invoke LangGraph and stream the final LLM response."""
    graph = st.session_state.rag_graph
    llm = st.session_state.llm
    checkpointer = st.session_state.checkpointer
    
    # Create thread config for LangGraph memory
    thread_id = f"{st.session_state.video_id}_{st.session_state.current_chat_id}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initialize state
    inputs = {
        "query": question,
        "chat_history": chat_history,
        "video_id": st.session_state.video_id,
        "vector_store": st.session_state.vector_store,
        "bm25_retriever": st.session_state.bm25_retriever,
        "llm": llm,
        "retrieval_attempt": 0,
        "context": "" # Clear context for new run
    }
    
    # Run graph with checkpointing
    # Graph execution to prepare the answer messages
    state = graph.invoke(inputs, config=config)
    
    # state["answer"] contains the messages array from generate_answer node
    messages = state.get("answer", [])
    
    full_response = ""
    
    def _token_generator():
        nonlocal full_response
        for chunk in llm.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content
                
    st.write_stream(_token_generator())
    
    return full_response

def render_chat_ui():
    st.subheader("💬 Chat with this Video")
    st.caption("Responses are grounded strictly in transcript context using Corrective RAG.")

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