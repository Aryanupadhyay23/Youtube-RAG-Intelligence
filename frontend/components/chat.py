import streamlit as st
from frontend.services.api import stream_chat, initialize_video, API_BASE_URL
from frontend.services.chat_storage import save_chat_messages, clear_current_chat
from frontend.utils.timestamp import linkify_timestamps


def render_chat_ui():
    """Render a clean, uncluttered RAG Chat interface with streaming responses."""
    video_id = st.session_state.get("video_id", "")
    chat_history = st.session_state.get("chat_history", [])

    # Render previous conversational turns
    for turn in chat_history:
        with st.chat_message("user", avatar="👤"):
            st.markdown(turn["user"])
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(linkify_timestamps(turn["ai"], video_id))

    # Read chat input at bottom
    user_question = st.chat_input("Ask about this video…")

    # Active Turn & Streaming Response
    if user_question:
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_question)

        chat_id = st.session_state.get("current_chat_id", "default_chat")
        if not video_id:
            st.error("⚠️ No video loaded. Please load a video first.")
            return

        with st.chat_message("assistant", avatar="🤖"):
            status_placeholder = st.empty()
            response_box = st.empty()
            full_response = ""
            has_error = False
            turn_committed = False

            def commit_response():
                """Persist the full or partial streamed answer to the chat that started it."""
                nonlocal turn_committed
                if turn_committed or not full_response:
                    return
                turn_committed = True

                updated_history = list(chat_history)
                updated_history.append({"user": user_question, "ai": full_response})
                save_chat_messages(chat_id, updated_history)

                # Only rebind the visible history if the user is still on this chat.
                if st.session_state.get("current_chat_id") == chat_id:
                    st.session_state.chat_history = updated_history

            try:

                def stream_with_retry():
                    for attempt in range(2):
                        encountered_eviction = False
                        for event in stream_chat(
                            video_id=video_id,
                            chat_id=chat_id,
                            query=user_question,
                            chat_history=[],
                            username=st.session_state.get("username", "default"),
                        ):
                            val_str = str(event.get("value", "")).lower()
                            if event["type"] == "error" and "not initialized" in val_str and attempt == 0:
                                encountered_eviction = True
                                break
                            yield event

                        if encountered_eviction:
                            status_placeholder.caption("🔄 Session expired. Re-initializing video...")
                            try:
                                initialize_video(video_id=video_id)
                            except Exception as reinit_err:
                                yield {"type": "error", "value": f"Re-initialization failed: {reinit_err}"}
                                break
                            continue
                        break

                for event in stream_with_retry():
                    event_type = event["type"]
                    value = event["value"]

                    if event_type == "status":
                        node_name = value.replace("Starting node: ", "")
                        labels = {
                            "rewrite_query": "🔍 Understanding your question...",
                            "hybrid_retrieve": "⚡ Finding relevant video moments...",
                            "evaluate_retrieval": "🎯 Checking video context...",
                            "correct_query": "🔄 Refining search...",
                            "web_search": "🌐 Gathering extra details from the web...",
                            "generate_answer": "✍️ Writing answer with timestamps...",
                        }
                        status_label = labels.get(node_name, f"⚙️ {value}...")
                        status_placeholder.caption(f"{status_label}")

                    elif event_type == "token":
                        status_placeholder.empty()
                        full_response += value
                        response_box.markdown(full_response + "▌")

                    elif event_type == "error":
                        status_placeholder.empty()
                        has_error = True
                        error_val = str(value).strip() if value else "An unexpected error occurred."
                        if "connect" in error_val.lower() or "Connection" in error_val:
                            st.error(f"🔌 Cannot reach the backend at {API_BASE_URL}.")
                        elif "timeout" in error_val.lower():
                            st.error("⏱️ Request timed out. Try again.")
                        else:
                            st.error(f"❌ {error_val}")

                if full_response:
                    response_box.markdown(linkify_timestamps(full_response, video_id))
                    status_placeholder.empty()
                elif not has_error:
                    response_box.markdown("*No response was generated. Please try again.*")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
            finally:
                # Persist partial output if the stream was interrupted after at least one token.
                commit_response()

            if turn_committed:
                st.rerun()

    # Compact chat actions at the very bottom
    if chat_history:
        st.write("")
        col_clear, col_exp = st.columns([1, 1])
        with col_clear:
            if st.button("🗑️ Clear Chat", key="btn_clear_chat", use_container_width=True):
                clear_current_chat()
                st.rerun()
        with col_exp:
            export_data = "\n".join(
                f"Turn {i}\n\nYou: {t['user']}\n\nAI: {t['ai']}\n" for i, t in enumerate(chat_history, 1)
            )
            st.download_button(
                label="⬇️ Export Chat (.txt)",
                data=export_data,
                file_name="chat_history.txt",
                mime="text/plain",
                use_container_width=True,
            )
