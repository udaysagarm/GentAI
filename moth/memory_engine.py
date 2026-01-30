import sqlite3
import os
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

DB_FILE = "moth_memory.db"

def init_db():
    """Calculates the database file path and creates the table if it doesn't exist."""
    # Ensure the DB file is created in the current working directory or a specific data directory
    # For now, we'll keep it simple and putting it in the root or same dir is fine, 
    # but the prompt asked for `moth_memory.db`.
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def save_memory(role: str, content: str):
    """Saves a message to the database."""
    if not content:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO messages (role, content) VALUES (?, ?)
    """, (role, content))
    
    conn.commit()
    conn.close()

def get_recent_memories(limit: int = 10):
    """
    Retrieves the last `limit` messages, formatted as LangChain objects.
    CRITICAL: Returned in Oldest -> Newest order for context window.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get last N messages based on ID descending, then flip them
    cursor.execute("""
        SELECT role, content FROM messages 
        ORDER BY id DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Rows are (role, content)
    # They come out Newest -> Oldest because of ORDER BY id DESC
    # We need to reverse them to be Oldest -> Newest
    rows_reversed = rows[::-1]
    
    formatted_messages = []
    for role, content in rows_reversed:
        if role == 'user':
            formatted_messages.append(HumanMessage(content=content))
        elif role == 'ai':
            formatted_messages.append(AIMessage(content=content))
            
    return formatted_messages
