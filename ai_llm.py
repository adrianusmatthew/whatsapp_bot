from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


class LanguageModel:
    def __init__(self, model_name="gpt-4o-2024-05-13"):
        # TODO: save to DB or some shit
        self.store = {}
        self.llm_model = ChatOpenAI(model=model_name)
        self.with_message_history = RunnableWithMessageHistory(
            self.llm_model,
            self.get_session_history
        )

    @staticmethod
    def create_session_id(contact: str) -> str:
        today = datetime.today().strftime('%Y-%m-%d')
        return f"{contact}-{today}"

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]

    def get_llm_response(self, prompt: str, session_id: str) -> str:
        config = {
            "configurable": {
                "session_id": session_id
            }
        }
        response = self.with_message_history.invoke(
            [HumanMessage(content=prompt)],
            config=config,
        )
        return response.content
