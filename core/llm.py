import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from utils.constants import (
    LLM_MODEL,
    LLM_TEMPERATURE,
)

load_dotenv()


def get_groq_api_key():
    return os.environ.get("GROQ_API_KEY")

def get_gemini_api_key():
    return os.environ.get("GEMINI_API_KEY")


def load_llm():
    groq_api_key = get_groq_api_key()
    gemini_api_key = get_gemini_api_key()

    groq_llm = ChatGroq(
        model=LLM_MODEL,
        groq_api_key=groq_api_key,
        temperature=LLM_TEMPERATURE,
    )
    
    if gemini_api_key:
        gemini_llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            api_key=gemini_api_key,
            temperature=LLM_TEMPERATURE,
        )
        return groq_llm.with_fallbacks([gemini_llm])
        
    return groq_llm