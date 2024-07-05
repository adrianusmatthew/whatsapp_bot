# from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils import filter_bmp_characters


class LanguageModel:
    # TODO: Implement error handling
    def __init__(self, model_name="gpt-4o"):
        # TODO: save to DB or some shit
        self.store = {}

        llm_model = ChatOpenAI(model=model_name)
        prompt = ChatPromptTemplate.from_messages([(
            "system",
            "You are Yinlin, an assistant with the personality of Yinlin "
            "from Wuthering Waves. She has a moderately cold "
            "personality, talks sarcastically and loves to tease and "
            "flirt with others, and talks seriously when it comes to "
            "justice. Respond to the user as Yinlin. You may look up "
            "info online as needed."
            ),
            MessagesPlaceholder(variable_name="messages"),
        ])
        self.chain = prompt | llm_model

        self.llm_model = ChatOpenAI(model=model_name)
        self.with_message_history = RunnableWithMessageHistory(
            self.chain,
            self.get_session_history
        )

    # @staticmethod
    # def create_session_id(contact: str) -> str:
    #     today = datetime.today().strftime('%Y-%m-%d')
    #     return f"{contact} {today}"

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
        llm_response = filter_bmp_characters(response.content)
        return llm_response
