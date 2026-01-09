"""
LangGraph Store implementation using SQLite for portable, local memory storage.
Based on LangGraph's Store API: https://docs.langchain.com/oss/python/langchain/long-term-memory
"""
import json
import sqlite3
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass
import threading


@dataclass
class StoreValue:
    """Value returned from store.get() with metadata"""
    value: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class SQLiteStore:
    """
    LangGraph-compatible Store implementation using SQLite.
    
    Stores memories as JSON documents organized by namespace (tuple) and key (str).
    Supports vector search if embeddings are provided.
    
    Usage:
        store = SQLiteStore("memories.db")
        store.put(("whatsapp", "user", "john"), "personality", {"traits": {...}})
        value = store.get(("whatsapp", "user", "john"), "personality")
        results = store.search(("whatsapp", "user", "john"), query="programming")
    """
    
    def __init__(self, db_path: str = "whatsapp_memory.db", index: Optional[Dict] = None):
        """
        Initialize SQLite store.
        
        Args:
            db_path: Path to SQLite database file (single portable file)
            index: Optional dict with 'embed' function and 'dims' for vector search
                   e.g., {"embed": embedding_fn, "dims": 768}
        """
        self.db_path = db_path
        self.index = index
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Main store table: namespace (JSON), key, value (JSON), embedding (BLOB), metadata (JSON)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    embedding BLOB,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(namespace, key)
                )
            """)
            
            # Index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_namespace_key 
                ON store(namespace, key)
            """)
            
            # Index for full-text search on value content
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS store_fts 
                USING fts5(namespace, key, value, content='store', content_rowid='id')
            """)
            
            conn.commit()
            conn.close()
    
    def _namespace_to_str(self, namespace: Tuple) -> str:
        """Convert namespace tuple to string for storage"""
        return json.dumps(namespace)
    
    def _str_to_namespace(self, namespace_str: str) -> Tuple:
        """Convert stored namespace string back to tuple"""
        return tuple(json.loads(namespace_str))
    
    def put(
        self, 
        namespace: Tuple[str, ...], 
        key: str, 
        value: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store a value in the store.
        
        Args:
            namespace: Tuple like ("whatsapp", "user", "contact_id")
            key: Key within the namespace
            value: Dictionary to store
            metadata: Optional metadata dictionary
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            namespace_str = self._namespace_to_str(namespace)
            value_str = json.dumps(value)
            metadata_str = json.dumps(metadata) if metadata else None
            
            # Generate embedding if index is configured
            embedding = None
            if self.index and "embed" in self.index:
                try:
                    # Create text representation for embedding
                    text_content = json.dumps(value)
                    embedding_bytes = self.index["embed"]([text_content])[0]
                    # Convert to bytes if needed
                    if isinstance(embedding_bytes, list):
                        import struct
                        embedding = struct.pack(f'{len(embedding_bytes)}f', *embedding_bytes)
                    else:
                        embedding = embedding_bytes
                except Exception as e:
                    print(f"Warning: Embedding generation failed: {e}")
            
            cursor.execute("""
                INSERT OR REPLACE INTO store 
                (namespace, key, value, embedding, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (namespace_str, key, value_str, embedding, metadata_str))
            
            # Update FTS index
            row_id = cursor.lastrowid
            cursor.execute("""
                INSERT OR REPLACE INTO store_fts(rowid, namespace, key, value)
                VALUES (?, ?, ?, ?)
            """, (row_id, namespace_str, key, value_str))
            
            conn.commit()
            conn.close()
    
    def get(self, namespace: Tuple[str, ...], key: str) -> Optional[StoreValue]:
        """
        Retrieve a value from the store.
        
        Args:
            namespace: Tuple like ("whatsapp", "user", "contact_id")
            key: Key within the namespace
            
        Returns:
            StoreValue with value and metadata, or None if not found
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            namespace_str = self._namespace_to_str(namespace)
            
            cursor.execute("""
                SELECT value, metadata FROM store
                WHERE namespace = ? AND key = ?
            """, (namespace_str, key))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                value = json.loads(row[0])
                metadata = json.loads(row[1]) if row[1] else None
                return StoreValue(value=value, metadata=metadata)
            return None
    
    def search(
        self,
        namespace: Tuple[str, ...],
        filter: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[StoreValue]:
        """
        Search for values in the store.
        
        Args:
            namespace: Tuple like ("whatsapp", "user", "contact_id")
            filter: Optional dict to filter by key-value pairs in stored values
            query: Optional text query for semantic/keyword search
            limit: Maximum number of results to return
            
        Returns:
            List of StoreValue objects, sorted by relevance
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            namespace_str = self._namespace_to_str(namespace)
            results = []
            
            if query:
                # Use FTS5 for text search
                cursor.execute("""
                    SELECT s.value, s.metadata, 
                           rank AS rank
                    FROM store s
                    JOIN store_fts fts ON s.id = fts.rowid
                    WHERE fts.namespace = ?
                    AND store_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (namespace_str, query, limit))
            else:
                # No query - get all items in namespace
                cursor.execute("""
                    SELECT value, metadata FROM store
                    WHERE namespace = ?
                    LIMIT ?
                """, (namespace_str, limit))
            
            rows = cursor.fetchall()
            
            # Apply filter if provided
            for row in rows:
                value = json.loads(row[0])
                metadata = json.loads(row[1]) if row[1] else None
                
                # Check filter matches
                if filter:
                    matches = True
                    for filter_key, filter_value in filter.items():
                        if filter_key not in value or value[filter_key] != filter_value:
                            matches = False
                            break
                    if not matches:
                        continue
                
                results.append(StoreValue(value=value, metadata=metadata))
            
            conn.close()
            return results
    
    def delete(self, namespace: Tuple[str, ...], key: str):
        """Delete a value from the store"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            namespace_str = self._namespace_to_str(namespace)
            
            cursor.execute("""
                DELETE FROM store
                WHERE namespace = ? AND key = ?
            """, (namespace_str, key))
            
            conn.commit()
            conn.close()
    
    def list_namespaces(self) -> List[Tuple[str, ...]]:
        """List all unique namespaces in the store"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT namespace FROM store")
            rows = cursor.fetchall()
            
            namespaces = [self._str_to_namespace(row[0]) for row in rows]
            conn.close()
            
            return namespaces
    
    def list_keys(self, namespace: Tuple[str, ...]) -> List[str]:
        """List all keys in a namespace"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            namespace_str = self._namespace_to_str(namespace)
            
            cursor.execute("""
                SELECT key FROM store
                WHERE namespace = ?
            """, (namespace_str,))
            
            keys = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return keys


def create_whatsapp_namespace(contact_name: str, is_group: bool = False) -> Tuple[str, ...]:
    """
    Helper function to create standardized namespace for WhatsApp contacts.
    
    Args:
        contact_name: Name or ID of the contact/group
        is_group: Whether this is a group chat
        
    Returns:
        Namespace tuple: ("whatsapp", "group"|"user", contact_name)
    """
    chat_type = "group" if is_group else "user"
    return ("whatsapp", chat_type, contact_name)
