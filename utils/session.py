import streamlit as st


SESSION_DEFAULTS = {
    "video_id": None,
    "metadata": None,
    "transcript_text": None,
    "transcript_segments": None,
    "vector_store": None,
    "rag_chain": None,
    "llm": None,
    "summary": None,
    "chat_history": [],
    "pending_question": None,
    "all_chats": {},
    "current_chat_id": None,
}


def initialize_session():

    for key, value in SESSION_DEFAULTS.items():

        if key not in st.session_state:
            st.session_state[key] = value


def clear_chat_history():

    st.session_state.chat_history = []


def clear_summary():

    st.session_state.summary = None


def clear_video_data():

    st.session_state.video_id = None
    st.session_state.metadata = None
    st.session_state.transcript_text = None
    st.session_state.transcript_segments = None
    st.session_state.vector_store = None
    st.session_state.rag_chain = None


def reset_video_state():

    clear_chat_history()
    clear_summary()