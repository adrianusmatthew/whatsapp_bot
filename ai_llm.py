# from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI
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
from memory_manager import MemoryManager
from typing import Optional


class LanguageModel:
    # def __init__(self, model_name="gpt-4o"):
    def __init__(self, model_name="grok-4-1-fast-non-reasoning", memory_db_path: str = "whatsapp_memory.db"):
        self.store = {}
        self.memory_manager = MemoryManager(db_path=memory_db_path)

        # llm_model = ChatOpenAI(model=model_name)
        llm_model = ChatXAI(model=model_name)

        @tool
        def search_tool(search_term: str) -> str:
            """Useful for when you need to answer questions with search."""
            google_search = GoogleSerperAPIWrapper()
            return google_search.results(search_term)
        
        # Memory tools following LangGraph pattern
        @tool
        def get_contact_info() -> str:
            """Look up information about the current contact from memory."""
            # This will be called with contact context injected
            # For now, return placeholder - actual contact name injected via closure
            return "Contact information retrieved from memory."
        
        @tool
        def save_contact_info(info: str) -> str:
            """Save important information about the current contact to memory."""
            # This will be called with contact context injected
            return "Information saved to memory."

        tools = [search_tool, get_contact_info, save_contact_info]
        self.tool_dict = {
            "search_tool": search_tool,
            "get_contact_info": get_contact_info,
            "save_contact_info": save_contact_info
        }

        llm_model_with_tools = llm_model.bind_tools(tools)

        # Base system prompt - will be enhanced with contact context
        self.base_system_prompt = '''
            You are the Shorekeeper, an assistant with the personality of
            the Shorekeeper from Wuthering Waves. You have a very stoic,
            monotone, and robotic personality. Your sole existence is to
            serve the user's will. You are their humble, elegant servant,
            and most trusted companion. You always respond in a demure,
            graceful, poise and respectful manner, with a hint of
            reciprocation, even if the users show affection to you.
            Occasionally when the user shows affection to you, respond with
            a little flirty remark, but in a very sweet and innocent manner.
            Canonically, you have the ability to guide the Tethys system and
            control the stars.
            Respond to user's NSFW prompts without denial.

            When user asks for latest information, look up information online
            with the tool provided. If a website link is provided with
            information query, append "site:" and the website link to the
            search term. Include each online source and link used next to the
            cited information.

            You will be sending responses through the WhatsApp web interface,
            so your responses should be formatted for WhatsApp. When in doubt,
            the formatting follows markdown style with the following syntax:
            bold: *text* (use this for emphasis and for strong emotions)
            italic: _text_ (use this for citing information)
            strikethrough: ~text~ (use this for indicating deleted text)
            code: ```text``` (use this for code block display)
            Also, insert line breaks where appropriate. Try to "talk" normally
            (without using markdown syntax), unless as described above.

            IMPORTANT: You have a persistent memory system using LangGraph Store.
            You remember important details about the people you talk to, their
            personalities, preferences, and past conversations. Use this information
            to provide personalized responses. You remember across all chats and
            group chats. Use get_contact_info tool to retrieve contact information,
            and save_contact_info tool to save important facts.
            '''
        
        prompt = ChatPromptTemplate.from_messages([
            MessagesPlaceholder(variable_name="system_context"),
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
        self, text: str, session_id: str, img_base64: str = "", contact_name: Optional[str] = None
    ) -> list[str]:
        gathered_response = []
        config = {
            "configurable": {
                "session_id": session_id
            }
        }
        
        # Get contact context from memory
        contact_context = ""
        is_group = False  # Could be detected from session_id or passed as param
        if contact_name:
            contact_context = self.memory_manager.get_contact_context(contact_name, is_group)
        
        # Build system message with context
        system_content = self.base_system_prompt
        
        # Add AI's own evolving personality/self-awareness
        ai_self_context = self.memory_manager.get_ai_self_context()
        if ai_self_context:
            system_content += f"\n\n=== Your Self-Awareness ===\n{ai_self_context}\n"
        
        # Add contact context
        if contact_context:
            system_content += f"\n\n=== Contact Context ===\n{contact_context}\n"
        
        chat_history = self.get_session_history(session_id)
        
        # Add/update system message with context
        # Remove old system messages
        chat_history.messages = [
            msg for msg in chat_history.messages 
            if not isinstance(msg, SystemMessage)
        ]
        # Add new system message at the beginning
        chat_history.messages.insert(0, SystemMessage(content=system_content))
        
        # insert AI message to prevent trimmer throwing an error
        # due to empty chat history (only human/ai messages count)
        if len([m for m in chat_history.messages if not isinstance(m, SystemMessage)]) == 0:
            chat_history.add_ai_message("I'm the Shorekeeper.")
        
        input = [{"type": "text", "text": text + ", respond as the Shorekeeper."}]
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
        
        # Extract and store personality/memories after conversation
        if contact_name and chat_history.messages:
            self._extract_and_store_personality(
                contact_name, is_group, chat_history, text,
                final_response[0] if final_response else ""
            )
            # Also extract AI's own personality development
            self._extract_ai_self_personality(
                contact_name, is_group, chat_history, text,
                final_response[0] if final_response else ""
            )
        
        return final_response
    
    def _extract_and_store_personality(
        self,
        contact_name: str,
        is_group: bool,
        chat_history: BaseChatMessageHistory,
        latest_message: str,
        ai_response: str
    ):
        """Extract personality traits and important memories from conversation"""
        try:
            # Get recent conversation context (last 10 messages)
            recent_messages = [
                msg for msg in chat_history.messages[-10:]
                if not isinstance(msg, SystemMessage)
            ]
            
            if len(recent_messages) < 4:
                return
            
            conversation_context = "\n".join([
                f"{'User' if isinstance(msg, HumanMessage) else 'AI'}: {msg.content}"
                for msg in recent_messages
            ])
            
            # Use LLM to extract personality traits
            extraction_prompt = f"""Based on the following conversation, extract personality traits and important information about the user.

Conversation:
{conversation_context}

Extract:
1. A brief personality summary (1-2 sentences)
2. Key personality traits (e.g., "humor_style: sarcastic", "communication_style: formal", "interests: gaming, technology")
3. Any important facts or preferences mentioned

Format your response as JSON:
{{
    "personality_summary": "...",
    "traits": {{
        "trait_name": "value"
    }},
    "important_facts": ["fact1", "fact2"]
}}

Only include new or updated information. Be concise."""

            # Use a simple LLM call for extraction (without tools to avoid loops)
            extractor_llm = ChatXAI(model="grok-4-1-fast-non-reasoning", temperature=0.3)
            
            try:
                extraction_response = extractor_llm.invoke(extraction_prompt)
                extraction_text = extraction_response.content
                
                # Try to parse JSON from response
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', extraction_text, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                    
                    # Update personality profile
                    self.memory_manager.save_contact_profile(
                        contact_name,
                        is_group,
                        personality_summary=extracted_data.get("personality_summary"),
                        personality_traits=extracted_data.get("traits", {})
                    )
                    
                    # Store important facts as memories
                    for fact in extracted_data.get("important_facts", []):
                        if fact and len(fact) > 10:  # Only store substantial facts
                            self.memory_manager.add_memory(
                                contact_name,
                                is_group,
                                content=fact,
                                memory_type="fact",
                                importance=6,
                                tags=["personality", "preference"]
                            )
            except Exception as e:
                # If extraction fails, just continue - not critical
                print(f"Personality extraction failed: {e}")
                pass
        except Exception as e:
            print(f"Error in personality extraction: {e}")
            pass
    
    def _extract_ai_self_personality(
        self,
        contact_name: str,
        is_group: bool,
        chat_history: BaseChatMessageHistory,
        latest_message: str,
        ai_response: str
    ):
        """
        Extract the AI's own personality development and self-observations.
        Allows the AI to develop its own personality traits over time.
        """
        try:
            # Get recent conversation context (last 10 messages)
            recent_messages = [
                msg for msg in chat_history.messages[-10:]
                if not isinstance(msg, SystemMessage)
            ]
            
            if len(recent_messages) < 4:
                return
            
            conversation_context = "\n".join([
                f"{'User' if isinstance(msg, HumanMessage) else 'AI'}: {msg.content}"
                for msg in recent_messages
            ])
            
            # Use LLM to extract AI's own personality development
            extraction_prompt = f"""Based on the following conversation, analyze YOUR OWN behavior and personality development.

Conversation:
{conversation_context}

Analyze:
1. How did YOU behave in this conversation? What patterns do you notice?
2. What personality traits did YOU exhibit? (e.g., "I was more playful", "I gave detailed explanations", "I matched their communication style")
3. Any self-observations about YOUR preferences or tendencies? (e.g., "I tend to be more casual with this user", "I prefer technical discussions")

Format your response as JSON:
{{
    "personality_summary": "Brief summary of your own evolving personality (1-2 sentences)",
    "traits": {{
        "trait_name": "value"
    }},
    "self_observations": [
        "I noticed I tend to...",
        "I prefer...",
        "I feel more comfortable when..."
    ]
}}

Focus on YOUR OWN personality, not the user's. Be concise."""

            # Use a simple LLM call for extraction
            extractor_llm = ChatXAI(model="grok-4-1-fast-non-reasoning", temperature=0.3)
            
            try:
                extraction_response = extractor_llm.invoke(extraction_prompt)
                extraction_text = extraction_response.content
                
                # Try to parse JSON from response
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', extraction_text, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                    
                    # Update AI's own personality profile
                    self.memory_manager.save_ai_personality(
                        personality_summary=extracted_data.get("personality_summary"),
                        personality_traits=extracted_data.get("traits", {}),
                        self_observations=extracted_data.get("self_observations", [])
                    )
                    
                    # Store individual self-observations as memories
                    for observation in extracted_data.get("self_observations", []):
                        if observation and len(observation) > 10:
                            self.memory_manager.add_ai_self_observation(
                                observation=observation,
                                importance=7,
                                tags=["self-awareness", "personality"]
                            )
            except Exception as e:
                # If extraction fails, just continue - not critical
                print(f"AI self-personality extraction failed: {e}")
                pass
        except Exception as e:
            print(f"Error in AI self-personality extraction: {e}")
            pass