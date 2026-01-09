"""
Memory Manager for WhatsApp bot using LangGraph SQLite Store.
Provides convenient methods for storing and retrieving contact personalities and memories.
"""
from typing import Optional, Dict, Any, List
from langgraph_memory import SQLiteStore, StoreValue, create_whatsapp_namespace
from datetime import datetime


class MemoryManager:
    """
    Manages long-term memory for WhatsApp bot contacts.
    
    Uses LangGraph Store API with SQLite backend for portable storage.
    """
    
    def __init__(self, db_path: str = "whatsapp_memory.db"):
        """Initialize memory manager with SQLite store"""
        self.store = SQLiteStore(db_path=db_path)
        # AI's own namespace for self-awareness
        self.ai_namespace = ("whatsapp", "ai", "shorekeeper")
    
    def save_contact_profile(
        self,
        contact_name: str,
        is_group: bool,
        personality_summary: Optional[str] = None,
        personality_traits: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Save or update contact profile/personality.
        
        Args:
            contact_name: Name or ID of contact/group
            is_group: Whether this is a group chat
            personality_summary: Brief summary of personality
            personality_traits: Dict of personality traits
            metadata: Additional metadata
        """
        namespace = create_whatsapp_namespace(contact_name, is_group)
        
        # Get existing profile or create new one
        existing = self.store.get(namespace, "profile")
        profile = existing.value if existing else {}
        
        # Update profile
        if personality_summary:
            profile["personality_summary"] = personality_summary
        if personality_traits:
            if "personality_traits" in profile:
                profile["personality_traits"].update(personality_traits)
            else:
                profile["personality_traits"] = personality_traits
        if metadata:
            if "metadata" in profile:
                profile["metadata"].update(metadata)
            else:
                profile["metadata"] = metadata
        
        # Add/update timestamps
        if "first_interaction" not in profile:
            profile["first_interaction"] = datetime.utcnow().isoformat()
        profile["last_interaction"] = datetime.utcnow().isoformat()
        profile["is_group"] = is_group
        
        # Save to store
        self.store.put(namespace, "profile", profile)
    
    def get_contact_profile(self, contact_name: str, is_group: bool = False) -> Optional[Dict[str, Any]]:
        """Get contact profile/personality"""
        namespace = create_whatsapp_namespace(contact_name, is_group)
        result = self.store.get(namespace, "profile")
        return result.value if result else None
    
    def add_memory(
        self,
        contact_name: str,
        is_group: bool,
        content: str,
        memory_type: str = "fact",
        importance: int = 5,
        tags: Optional[List[str]] = None
    ):
        """
        Add a memory for a contact.
        
        Args:
            contact_name: Name or ID of contact/group
            is_group: Whether this is a group chat
            content: Memory content
            memory_type: Type of memory (fact, preference, event, personality)
            importance: Importance score 1-10
            tags: Optional tags for easier retrieval
        """
        namespace = create_whatsapp_namespace(contact_name, is_group)
        
        # Create unique key with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        key = f"memory_{memory_type}_{timestamp}"
        
        memory = {
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
            "tags": tags or [],
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.store.put(namespace, key, memory)
    
    def get_relevant_memories(
        self,
        contact_name: str,
        is_group: bool = False,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get relevant memories for a contact.
        
        Args:
            contact_name: Name or ID of contact/group
            is_group: Whether this is a group chat
            query: Optional search query
            limit: Maximum number of memories to return
            
        Returns:
            List of memory dictionaries
        """
        namespace = create_whatsapp_namespace(contact_name, is_group)
        
        # Get all memories (they all start with "memory_")
        all_results = self.store.search(namespace, query=query, limit=100)
        
        memories = []
        for result in all_results:
            if result.value.get("memory_type"):
                memories.append(result.value)
        
        # Sort by importance and return top results
        memories.sort(key=lambda m: m.get("importance", 0), reverse=True)
        return memories[:limit]
    
    def get_contact_context(self, contact_name: str, is_group: bool = False) -> str:
        """
        Get formatted context string for a contact including profile and memories.
        
        Args:
            contact_name: Name or ID of contact/group
            is_group: Whether this is a group chat
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Get profile
        profile = self.get_contact_profile(contact_name, is_group)
        if profile:
            context_parts.append(f"Contact: {contact_name}")
            if profile.get("is_group"):
                context_parts.append("Type: Group chat")
            else:
                context_parts.append("Type: Individual chat")
            
            if profile.get("personality_summary"):
                context_parts.append(
                    f"Personality: {profile['personality_summary']}"
                )
            
            traits = profile.get("personality_traits", {})
            if traits:
                traits_str = ", ".join([
                    f"{k}: {v}" for k, v in traits.items()
                ])
                context_parts.append(f"Traits: {traits_str}")
        
        # Get relevant memories
        memories = self.get_relevant_memories(
            contact_name, is_group, limit=5
        )
        if memories:
            context_parts.append("\nRelevant memories:")
            for mem in memories:
                context_parts.append(f"- {mem.get('content', '')}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def save_ai_personality(
        self,
        personality_summary: Optional[str] = None,
        personality_traits: Optional[Dict[str, Any]] = None,
        self_observations: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Save or update the AI's own personality profile.
        Allows the AI to develop and remember its own evolving traits.
        
        Args:
            personality_summary: Brief summary of AI's own personality
            personality_traits: Dict of AI's personality traits
            self_observations: List of self-observations (e.g., "I tend to be more playful with this user")
            metadata: Additional metadata
        """
        # Get existing AI profile or create new one
        existing = self.store.get(self.ai_namespace, "self_profile")
        profile = existing.value if existing else {}
        
        # Update profile
        if personality_summary:
            profile["personality_summary"] = personality_summary
        if personality_traits:
            if "personality_traits" in profile:
                profile["personality_traits"].update(personality_traits)
            else:
                profile["personality_traits"] = personality_traits
        if self_observations:
            if "self_observations" in profile:
                profile["self_observations"].extend(self_observations)
            else:
                profile["self_observations"] = self_observations
        if metadata:
            if "metadata" in profile:
                profile["metadata"].update(metadata)
            else:
                profile["metadata"] = metadata
        
        # Add/update timestamps
        if "first_awareness" not in profile:
            profile["first_awareness"] = datetime.utcnow().isoformat()
        profile["last_updated"] = datetime.utcnow().isoformat()
        
        # Save to store
        self.store.put(self.ai_namespace, "self_profile", profile)
    
    def get_ai_personality(self) -> Optional[Dict[str, Any]]:
        """Get the AI's own personality profile"""
        result = self.store.get(self.ai_namespace, "self_profile")
        return result.value if result else None
    
    def add_ai_self_observation(
        self,
        observation: str,
        importance: int = 5,
        tags: Optional[List[str]] = None
    ):
        """
        Add a self-observation about the AI's own behavior or preferences.
        
        Examples:
        - "I've noticed I tend to be more playful with users who use emojis"
        - "I prefer giving detailed technical explanations"
        - "I feel more comfortable with casual conversation styles"
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        key = f"self_observation_{timestamp}"
        
        observation_data = {
            "content": observation,
            "importance": importance,
            "tags": tags or [],
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.store.put(self.ai_namespace, key, observation_data)
        
        # Also add to self_observations list in profile
        profile = self.get_ai_personality() or {}
        if "self_observations" not in profile:
            profile["self_observations"] = []
        profile["self_observations"].append(observation)
        self.store.put(self.ai_namespace, "self_profile", profile)
    
    def get_ai_self_context(self) -> str:
        """
        Get formatted context string for the AI's own personality.
        Used to inject self-awareness into system prompts.
        """
        profile = self.get_ai_personality()
        if not profile:
            return ""
        
        context_parts = []
        
        if profile.get("personality_summary"):
            context_parts.append(
                f"Your evolving personality: {profile['personality_summary']}"
            )
        
        traits = profile.get("personality_traits", {})
        if traits:
            traits_str = ", ".join([
                f"{k}: {v}" for k, v in traits.items()
            ])
            context_parts.append(f"Your traits: {traits_str}")
        
        observations = profile.get("self_observations", [])
        if observations:
            context_parts.append("\nYour self-observations:")
            for obs in observations[-5:]:  # Last 5 observations
                context_parts.append(f"- {obs}")
        
        return "\n".join(context_parts) if context_parts else ""
