import time

import streamlit as st


def create_new_chat():

    chat_id = f"chat_{int(time.time())}"

    st.session_state.all_chats[chat_id] = {
        "title": "New Chat",
        "messages": [],
        "created_at": time.strftime(
            "%H:%M"
        ),
    }

    st.session_state.current_chat_id = chat_id

    st.session_state.chat_history = []


def switch_chat(chat_id: str):

    st.session_state.current_chat_id = chat_id

    messages = (
        st.session_state
        .all_chats[chat_id]["messages"]
    )

    st.session_state.chat_history = messages


def save_current_chat(messages):

    current_chat_id = (
        st.session_state.current_chat_id
    )

    if (
        current_chat_id
        not in st.session_state.all_chats
    ):
        return

    st.session_state.all_chats[
        current_chat_id
    ]["messages"] = messages

    if messages:

        first_message = messages[0]["user"]

        title = (
            first_message[:35] + "..."
            if len(first_message) > 35
            else first_message
        )

        st.session_state.all_chats[
            current_chat_id
        ]["title"] = title


def delete_current_chat():

    current_chat_id = (
        st.session_state.current_chat_id
    )

    if (
        current_chat_id
        in st.session_state.all_chats
    ):

        del st.session_state.all_chats[
            current_chat_id
        ]

    st.session_state.chat_history = []

    if st.session_state.all_chats:

        first_chat_id = list(
            st.session_state.all_chats.keys()
        )[0]

        switch_chat(first_chat_id)

    else:

        create_new_chat()


def initialize_chat_state():

    if (
        not st.session_state.current_chat_id
        and not st.session_state.all_chats
    ):

        create_new_chat()