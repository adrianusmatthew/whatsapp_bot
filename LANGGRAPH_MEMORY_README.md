# LangGraph Memory System for WhatsApp Bot

## Overview

This implementation uses **LangGraph's Store API** with a **SQLite backend** for portable, local long-term memory storage. All memories are stored in a single SQLite database file (`whatsapp_memory.db`) that can be easily moved, backed up, or deployed.

Based on: [LangChain Long-term Memory Documentation](https://docs.langchain.com/oss/python/langchain/long-term-memory)

## Architecture

### Components

1. **`SQLiteStore`** (`langgraph_memory.py`)
   - Implements LangGraph's Store interface
   - Uses SQLite for persistent storage
   - Supports namespaced storage (like folders)
   - Includes full-text search via SQLite FTS5
   - Thread-safe with connection locking

2. **`MemoryManager`** (`memory_manager.py`)
   - High-level wrapper for WhatsApp bot
   - Provides convenient methods for contact profiles and memories
   - Handles namespace creation automatically

3. **Integrated `LanguageModel`** (`ai_llm.py`)
   - Automatically retrieves contact context before responses
   - Extracts and stores personality traits after conversations
   - Injects memory context into system prompts

## How It Works

### Namespace Structure

Memories are organized by namespace tuples:
- Individual chats: `("whatsapp", "user", "contact_name")`
- Group chats: `("whatsapp", "group", "group_name")`

### Storage Format

**Contact Profiles** (key: `"profile"`):
```json
{
  "personality_summary": "Brief description...",
  "personality_traits": {
    "humor_style": "sarcastic",
    "communication_style": "formal",
    "interests": ["gaming", "technology"]
  },
  "is_group": false,
  "first_interaction": "2025-01-15T10:30:00",
  "last_interaction": "2025-01-15T12:45:00",
  "metadata": {}
}
```

**Memories** (key: `"memory_{type}_{timestamp}"`):
```json
{
  "content": "User loves Python programming",
  "memory_type": "fact",
  "importance": 6,
  "tags": ["programming", "preference"],
  "created_at": "2025-01-15T10:30:00"
}
```

## Usage

### Automatic Operation

The memory system works automatically:

1. **On first message**: Contact is registered in memory
2. **Before each response**: Relevant memories are retrieved and injected into context
3. **After conversations**: Personality traits are extracted and stored (after 4+ messages)

### Manual Memory Management

You can also manually manage memories:

```python
from memory_manager import MemoryManager

memory_manager = MemoryManager("whatsapp_memory.db")

# Save contact profile
memory_manager.save_contact_profile(
    contact_name="John Doe",
    is_group=False,
    personality_summary="Friendly and tech-savvy",
    personality_traits={"interests": ["Python", "AI"]}
)

# Add a memory
memory_manager.add_memory(
    contact_name="John Doe",
    is_group=False,
    content="Prefers short, direct messages",
    memory_type="preference",
    importance=8,
    tags=["communication"]
)

# Get contact context
context = memory_manager.get_contact_context("John Doe")
print(context)
```

### Direct Store Access

For advanced usage, access the store directly:

```python
from langgraph_memory import SQLiteStore, create_whatsapp_namespace

store = SQLiteStore("whatsapp_memory.db")

# Create namespace
namespace = create_whatsapp_namespace("John Doe", is_group=False)

# Store data
store.put(namespace, "custom_key", {"data": "value"})

# Retrieve data
value = store.get(namespace, "custom_key")
print(value.value)  # {"data": "value"}

# Search
results = store.search(namespace, query="programming", limit=5)
for result in results:
    print(result.value)
```

## Database Location

The SQLite database is stored as **`whatsapp_memory.db`** in your project root directory.

**Portability**: This single file contains all memories and can be:
- Copied to another machine
- Backed up easily
- Version controlled (if desired)
- Moved between environments

## Features

✅ **Persistent Storage** - All memories survive bot restarts  
✅ **Portable** - Single SQLite file, no server needed  
✅ **Thread-Safe** - Safe for concurrent access  
✅ **Full-Text Search** - Fast keyword search via SQLite FTS5  
✅ **Automatic Personality Extraction** - Learns from conversations  
✅ **Cross-Chat Memory** - Remembers across different conversations  
✅ **Group Chat Support** - Distinguishes individual vs group chats  

## Future Enhancements

1. **Vector Embeddings**: Add semantic similarity search using embeddings
2. **Memory Summarization**: Periodically summarize old conversations
3. **Memory Expiration**: Auto-remove low-importance old memories
4. **Export/Import**: Tools to backup and restore memories

## Technical Details

### SQLite Schema

```sql
CREATE TABLE store (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    embedding BLOB,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(namespace, key)
);

CREATE VIRTUAL TABLE store_fts USING fts5(
    namespace, key, value, 
    content='store', content_rowid='id'
);
```

### Thread Safety

The store uses `threading.Lock()` to ensure thread-safe database operations, making it safe for concurrent access in multi-threaded environments.

## Comparison with Previous Implementation

| Feature | Custom SQLite | LangGraph Store |
|---------|--------------|-----------------|
| Portability | ✅ Single file | ✅ Single file |
| LangGraph Compatible | ❌ | ✅ |
| Standard API | ❌ | ✅ |
| Full-text Search | ✅ | ✅ |
| Vector Search Ready | ❌ | ✅ (with embeddings) |
| Future-proof | ⚠️ Custom | ✅ Standard |

The LangGraph Store implementation provides a standard, future-proof API that aligns with LangChain/LangGraph best practices while maintaining the portability benefits of SQLite.
