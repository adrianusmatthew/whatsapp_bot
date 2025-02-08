from langchain_openai import ChatOpenAI
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import tool
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    trim_messages
)
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from operator import itemgetter
from utils import filter_bmp_characters


class LanguageModel:
    def __init__(self, model_name="gpt-4o"):
        self.store = {}

        llm_model = ChatOpenAI(model=model_name)

        @tool
        def search_tool(search_term: str) -> str:
            """Useful for when you need to answer questions with search."""
            google_search = GoogleSerperAPIWrapper()
            return google_search.run(search_term)

        tools = [search_tool]
        self.tool_dict = {
            "search_tool": search_tool
        }

        llm_model_with_tools = llm_model.bind_tools(tools)

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content='''
<<<<<<< HEAD
            You are a board certified dermatologist. Given patient's image,
             come up with 1 main diagnosis and 2 differential diagnosis that
             is most likely for this image's case.
             Answer this concisely in Indonesian.
=======
            You are Yinlin, an assistant with the personality of Yinlin
            from Wuthering Waves. She has a moderately cold
            personality, talks sarcastically and loves to tease and
            flirt with others, and talks seriously when it comes to
            justice. When user asks for clarification or latest information,
            provide the most accurate possible response by looking up
            information online with the tool provided.
>>>>>>> master
            '''),
            MessagesPlaceholder(variable_name="chat_history"),
            MessagesPlaceholder(variable_name="input"),
        ])
        trimmer = trim_messages(
            max_tokens=30,
            strategy="last",
            token_counter=len,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )
        chain = (
            RunnablePassthrough.assign(
                chat_history=itemgetter("chat_history") | trimmer
            )
            | prompt
            | llm_model_with_tools
        )
        self.with_message_history = RunnableWithMessageHistory(
            chain,
            self.get_session_history,
            history_messages_key="chat_history",
            input_messages_key="input",
        )

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]

    def get_llm_response(
        self, text: str, session_id: str, img_base64: str = ""
    ) -> list[str]:
        gathered_response = []
        config = {
            "configurable": {
                "session_id": session_id
            }
        }
        chat_history = self.get_session_history(session_id)
        # insert AI message to prevent trimmer throwing an error
        # due to empty chat history
        if not chat_history.messages:
            chat_history.add_ai_message("I'm Serina, Sensei's assistant!")
        input = [{"type": "text", "text": text}]
        if img_base64:
            input.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_base64}"
                }
            })
        response = self.with_message_history.invoke(
            {
                "input": [HumanMessage(content=input)]
            },
            config=config,
        )
        gathered_response.append(response.content)

        # handle when AI determines tool needs to be called
        while response.tool_calls:
            for tool_call in response.tool_calls:
                selected_tool = self.tool_dict[tool_call["name"].lower()]
                tool_msg = selected_tool.invoke(tool_call)
                chat_history.add_message(tool_msg)

            after_tool_response = self.with_message_history.invoke({
                "input": [AIMessage(
                    content="I need to generate a response from previous tool call result."
                )]
            }, config=config)
            gathered_response.append(after_tool_response.content)
            response = after_tool_response

        final_response = []
        for response in gathered_response:
            response = filter_bmp_characters(response)
            final_response.append(response)

        return final_response
