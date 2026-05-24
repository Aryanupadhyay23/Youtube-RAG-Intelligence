import streamlit as st

from services.chat_service import (
    create_new_chat,
    switch_chat,
    delete_current_chat,
)

from utils.constants import APP_TITLE, APP_CAPTION

from config import (
    IS_HUGGINGFACE,
    GROQ_API_KEY,
    SUPADATA_KEYS,
)


def _render_env_status():
    """Show where secrets are being loaded from."""

    if IS_HUGGINGFACE:
        st.success("🤗 Running on HuggingFace Spaces", icon="✅")
        source = "HuggingFace Secrets"
    else:
        st.info("💻 Running locally", icon="🖥️")
        source = ".env file"

    with st.expander("🔑 Key Status"):

        groq_ok = bool(GROQ_API_KEY)
        supa_ok = len(SUPADATA_KEYS) > 0

        st.markdown(
            f"**Source:** `{source}`"
        )

        st.markdown(
            f"{'✅' if groq_ok else '❌'} "
            f"`GROQ_API_KEY` "
            f"{'loaded' if groq_ok else 'missing'}"
        )

        st.markdown(
            f"{'✅' if supa_ok else '❌'} "
            f"`SUPADATA_KEY` "
            f"({len(SUPADATA_KEYS)} key{'s' if len(SUPADATA_KEYS) != 1 else ''} "
            f"{'loaded' if supa_ok else 'missing'})"
        )


def render_sidebar():

    with st.sidebar:

        st.title(f"▶️ {APP_TITLE}")
        st.caption(APP_CAPTION)

        st.divider()

        # ── environment & key status ──────────────────────
        _render_env_status()

        st.divider()

        # ── video input ───────────────────────────────────
        video_url = st.text_input(
            "YouTube URL",
            placeholder="https://youtube.com/watch?v=…",
        )

        load_button = st.button(
            "🚀 Load Video",
            type="primary",
            use_container_width=True,
        )

        st.divider()

        # ── new chat ──────────────────────────────────────
        if st.button(
            "➕ New Chat",
            use_container_width=True,
        ):
            create_new_chat()
            st.rerun()

        # ── chat list ─────────────────────────────────────
        if st.session_state.all_chats:

            st.subheader("💬 Chats")

            sorted_chats = sorted(
                st.session_state.all_chats.items(),
                reverse=True,
            )

            for chat_id, chat_data in sorted_chats:

                is_current = (
                    chat_id == st.session_state.current_chat_id
                )

                label = (
                    f"▸ {chat_data['title']}"
                    if is_current
                    else chat_data["title"]
                )

                if st.button(
                    label,
                    key=chat_id,
                    type="primary" if is_current else "secondary",
                    use_container_width=True,
                ):
                    switch_chat(chat_id)
                    st.rerun()

        # ── delete chat ───────────────────────────────────
        if st.session_state.current_chat_id:

            st.divider()

            if st.button(
                "🗑️ Delete Current Chat",
                use_container_width=True,
            ):
                delete_current_chat()
                st.rerun()

    return video_url, load_button