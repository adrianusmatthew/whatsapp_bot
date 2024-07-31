from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils import filter_bmp_characters


class LanguageModel:
    def __init__(self, model_name="gpt-4o"):
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

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]

    def get_llm_response(
        self, text: str, session_id: str, img_base64: str = ""
    ) -> str:
        config = {
            "configurable": {
                "session_id": session_id
            }
        }
        prompt = [{"type": "text", "text": text}]
        if img_base64:
            prompt.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_base64}"
                }
            })
        response = self.with_message_history.invoke(
            [HumanMessage(content=prompt)],
            config=config,
        )
        llm_response = filter_bmp_characters(response.content)
        return llm_response
