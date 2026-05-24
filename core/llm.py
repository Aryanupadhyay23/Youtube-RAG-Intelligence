import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from utils.constants import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)

load_dotenv()


def get_groq_api_key():
    return os.environ.get("GROQ_API_KEY")


def load_llm():

    groq_api_key = get_groq_api_key()

    return ChatGroq(
        model=LLM_MODEL,
        groq_api_key=groq_api_key,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )