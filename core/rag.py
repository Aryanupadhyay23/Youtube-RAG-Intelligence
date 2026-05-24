from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)

from langchain_core.runnables import RunnableLambda

from langchain_core.output_parsers import StrOutputParser

from langchain_core.messages import HumanMessage, AIMessage

from core.prompts import SYSTEM_PROMPT


def format_documents(documents):

    return "\n\n".join(
        doc.page_content for doc in documents
    )


def get_langchain_history(chat_history):
    """Convert chat_history list of dicts → LangChain message objects."""

    messages = []

    for turn in chat_history:
        messages.append(HumanMessage(content=turn["user"]))
        messages.append(AIMessage(content=turn["ai"]))

    return messages


def build_rag_chain(vector_store, llm):

    retriever = vector_store.as_retriever(
        search_kwargs={"k": 4}
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    def build_input(data):

        documents = retriever.invoke(data["question"])

        return {
            "context": format_documents(documents),
            "question": data["question"],
            "chat_history": data.get("chat_history", []),
        }

    chain = (
        RunnableLambda(build_input)
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def ask_question(rag_chain, question, chat_history):
    """Non-streaming invoke — kept for compatibility."""

    lc_history = get_langchain_history(chat_history)

    return rag_chain.invoke({
        "question": question,
        "chat_history": lc_history,
    })