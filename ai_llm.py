from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# TODO: implement store with DB functionality
store = {}
llm_model = ChatOpenAI(model="gpt-3.5-turbo")


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()

    return store[session_id]


with_message_history = RunnableWithMessageHistory(
    llm_model,
    get_session_history
)


def create_session_id(contact: str) -> str:
    today = datetime.today().strftime('%Y-%m-%d')
    return f"{contact}-{today}"


def get_llm_response(prompt: str, session_id: str) -> str:
    config = {
        "configurable": {
            "session_id": session_id
        }
    }
    response = with_message_history.invoke(
        [HumanMessage(content=prompt)],
        config=config,
    )

    return response.content
