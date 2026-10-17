import streamlit as st
from frontend.utils.constants import APP_TITLE
from frontend.services.chat_storage import (
    get_current_username,
    create_new_chat,
    switch_chat,
    delete_chat,
    switch_user,
    get_saved_user_sessions,
)
from frontend.services.api import delete_remote_chat


def render_sidebar():
    """Render a clean sidebar focused on user identity, automatic conversation memory, and session management."""
    with st.sidebar:
        # Brand header
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-radius: 12px; background: rgba(30, 58, 138, 0.25); border: 1px solid rgba(59, 130, 246, 0.25); margin-bottom: 1rem;">
                <div style="width: 34px; height: 34px; border-radius: 8px; background: linear-gradient(135deg, #2563eb, #4f46e5); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 1rem; flex-shrink: 0;">
                    ▶
                </div>
                <div style="font-weight: 700; font-size: 1.05rem; color: #ffffff; letter-spacing: -0.01em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {APP_TITLE}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── User Account / Memory Profile ─────────────────────────────────────
        current_user = get_current_username()
        is_default = (current_user == "default")

        st.markdown(
            f"""
            <div style="padding: 12px; border-radius: 12px; background: rgba(15, 23, 42, 0.7); border: 1px solid {'rgba(59, 130, 246, 0.3)' if is_default else 'rgba(16, 185, 129, 0.3)'}; margin-bottom: 0.75rem;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                    <span style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8;">User Profile</span>
                    <span style="font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 9999px; background: {'rgba(59, 130, 246, 0.2)' if is_default else 'rgba(16, 185, 129, 0.2)'}; color: {'#60a5fa' if is_default else '#34d399'}; border: 1px solid {'rgba(59, 130, 246, 0.35)' if is_default else 'rgba(16, 185, 129, 0.35)'};">
                        {'Default Mode' if is_default else f'@{current_user}'}
                    </span>
                </div>
                <p style="font-size: 0.78rem; color: #94a3b8; line-height: 1.4; margin: 0 0 8px 0;">
                    {'Conversations are saved automatically under <b>default</b>. Enter your username below to save and reload your personal chats.' if is_default else f'Active user: <b>@{current_user}</b>. All conversations you conduct are automatically stored in memory.'}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Username Input & Switcher
        if is_default:
            col_in, col_btn = st.columns([3, 2])
            with col_in:
                user_input = st.text_input(
                    "Username",
                    key="sidebar_username_input",
                    placeholder="Enter username...",
                    label_visibility="collapsed",
                )
            with col_btn:
                if st.button("💾 Load Chats", use_container_width=True, type="primary"):
                    if user_input and user_input.strip():
                        switch_user(user_input.strip())
                        st.rerun()
                    else:
                        st.warning("Type a username first.")
        else:
            col_switch_in, col_switch_btn = st.columns([3, 2])
            with col_switch_in:
                switch_prompt = st.text_input(
                    "Switch User",
                    key="sidebar_change_user_input",
                    placeholder="Switch user...",
                    label_visibility="collapsed",
                )
            with col_switch_btn:
                if st.button("🔄 Switch", use_container_width=True):
                    if switch_prompt and switch_prompt.strip():
                        switch_user(switch_prompt.strip())
                        st.rerun()
            if st.button("↩️ Reset to Default Mode", use_container_width=True):
                switch_user("default")
                st.rerun()

        st.divider()

        has_video = bool(
            st.session_state.get("video_id")
            and st.session_state.get("transcript_text")
        )

        # ── Conversation Memories ─────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; padding: 6px 2px 8px 2px; display: flex; align-items: center; justify-content: space-between;">
                <span>Conversation Memories</span>
                <span style="font-size: 10px; color: #60a5fa; font-weight: 600;">{'@' + current_user}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if has_video:
            # Active video actions (New Chat & Switch Video)
            col_nc, col_sw = st.columns([1, 1])
            with col_nc:
                if st.button("➕ New Chat", type="primary", use_container_width=True):
                    create_new_chat()
                    st.rerun()
            with col_sw:
                if st.button("🔄 Switch Video", use_container_width=True, help="Clear active video and load a new YouTube link"):
                    from frontend.utils.session import reset_video_state
                    reset_video_state()
                    st.session_state.pop("main_url_field", None)
                    st.rerun()

            # Chat session list for current video
            all_chats = st.session_state.get("all_chats", {})
            current_id = st.session_state.get("current_chat_id")

            if all_chats:
                for chat_id, chat_data in sorted(all_chats.items(), reverse=True):
                    is_current = chat_id == current_id
                    title = chat_data.get("title", "New Chat")
                    display_title = (title[:36] + "…") if len(title) > 36 else title

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
                        if st.button("🗑️", key=f"del_{chat_id}", use_container_width=True):
                            delete_chat(chat_id)
                            st.rerun()
            else:
                st.caption("No chats yet for this video.")

        else:
            # When no video is currently loaded: display all saved conversation memories
            saved_sessions = get_saved_user_sessions(current_user)

            if saved_sessions:
                st.caption(f"Showing {len(saved_sessions)} saved conversation(s) for @{current_user}:")
                for s in saved_sessions:
                    chat_id = s.get("chat_id", "")
                    vid_id = s.get("video_id", "")
                    title = s.get("title", "Conversation")
                    display_title = (title[:32] + "…") if len(title) > 32 else title
                    updated = s.get("updated_at", "")

                    with st.container():
                        st.markdown(
                            f"""
                            <div style="padding: 10px 12px; border-radius: 10px; background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(59, 130, 246, 0.2); margin-bottom: 6px;">
                                <div style="font-weight: 600; font-size: 0.85rem; color: #ffffff; margin-bottom: 2px;">💬 {display_title}</div>
                                <div style="font-size: 0.72rem; color: #94a3b8;">🎬 Video: <code style="color: #60a5fa;">{vid_id}</code> • 🕒 {updated}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        col_open, col_remove = st.columns([4, 1])
                        with col_open:
                            if st.button("▶ Open Chat", key=f"open_saved_{chat_id}", use_container_width=True):
                                st.session_state.submitted_video_url = f"https://www.youtube.com/watch?v={vid_id}"
                                st.session_state.target_chat_id = chat_id
                                st.rerun()
                        with col_remove:
                            if st.button("🗑️", key=f"del_saved_{chat_id}", use_container_width=True):
                                delete_remote_chat(chat_id, video_id=vid_id, username=current_user)
                                st.rerun()
            else:
                # Welcoming empty state card
                st.markdown(
                    f"""
                    <div style="padding: 20px 14px; border-radius: 12px; background: rgba(15, 23, 42, 0.6); border: 1px dashed rgba(59, 130, 246, 0.3); text-align: center; margin-top: 6px;">
                        <span style="font-size: 1.6rem; display: block; margin-bottom: 6px;">🧠</span>
                        <div style="font-size: 0.88rem; font-weight: 600; color: #ffffff; margin-bottom: 4px;">No Saved Conversations Yet</div>
                        <p style="font-size: 0.76rem; color: #94a3b8; line-height: 1.4; margin: 0;">
                            Paste any YouTube video link to start chatting. All conversations for <b>@{current_user}</b> are automatically preserved here.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
