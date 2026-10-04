import streamlit as st
from frontend.utils.constants import APP_TITLE
from frontend.services.chat_storage import create_new_chat, switch_chat, delete_current_chat


def render_sidebar():
    """Render a clean, minimal sidebar focused on chat session management."""
    with st.sidebar:
        # Brand header
        st.markdown(
            f"""
            <div class="flex items-center gap-3 p-3.5 rounded-xl bg-gradient-to-r from-blue-950/60 via-slate-900/80 to-blue-900/30 border border-blue-500/20 shadow-lg shadow-blue-950/20 mb-3">
                <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-black text-base shadow-md shadow-blue-500/30 flex-shrink-0">
                    ▶
                </div>
                <div class="font-extrabold text-base tracking-tight text-white font-sans truncate">
                    {APP_TITLE}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        has_video = bool(
            st.session_state.get("video_id")
            and st.session_state.get("transcript_text")
        )

        if has_video:
            # New Chat button
            if st.button("➕ New Chat", type="primary", use_container_width=True):
                create_new_chat()
                st.rerun()

            st.markdown(
                """
                <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-1 pt-3 pb-1.5 flex items-center gap-2">
                    <span>Chat History</span>
                    <div class="flex-1 h-px bg-slate-800"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Chat session list
            all_chats = st.session_state.get("all_chats", {})
            current_id = st.session_state.get("current_chat_id")

            if all_chats:
                for chat_id, chat_data in sorted(all_chats.items(), reverse=True):
                    is_current = chat_id == current_id
                    title = chat_data.get("title", "New Chat")

                    # Truncate long titles
                    display_title = (title[:40] + "…") if len(title) > 40 else title

                    col_chat, col_del = st.columns([5, 1])

                    with col_chat:
                        btn_type = "primary" if is_current else "secondary"
                        label = f"💬 {display_title}" if is_current else display_title

                        if st.button(
                            label,
                            key=f"chat_{chat_id}",
                            type=btn_type,
                            use_container_width=True,
                        ):
                            switch_chat(chat_id)
                            st.rerun()

                    with col_del:
                        if st.button(
                            "🗑️",
                            key=f"del_{chat_id}",
                            use_container_width=True,
                        ):
                            # Delete this specific chat
                            if chat_id in st.session_state.all_chats:
                                del st.session_state.all_chats[chat_id]

                            # If we deleted the active chat, switch to another
                            if chat_id == current_id:
                                st.session_state.chat_history = []
                                remaining = st.session_state.all_chats
                                if remaining:
                                    switch_chat(list(remaining.keys())[0])
                                else:
                                    create_new_chat()

                            st.rerun()

            # Load different video option
            st.divider()
            if st.button("🔄 Load Different Video", use_container_width=True):
                from frontend.utils.session import reset_video_state
                reset_video_state()
                st.rerun()

        else:
            st.caption("💡 Paste a YouTube link to start chatting.")
