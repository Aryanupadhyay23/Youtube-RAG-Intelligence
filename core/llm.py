import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from utils.constants import (
    LLM_TEMPERATURE,
)

load_dotenv()


def get_gemini_api_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def load_llm():
    gemini_api_key = get_gemini_api_key()

    gemini_llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        api_key=gemini_api_key,
        temperature=LLM_TEMPERATURE,
    )

    return gemini_llm