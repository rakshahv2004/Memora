
import sqlite3
from datetime import datetime

DB_NAME = "memora.db"


def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_memory(content, category="General"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO memories (content, category, created_at) VALUES (?, ?, ?)",
        (content, category, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()


def get_memories():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, content, category, created_at FROM memories ORDER BY id DESC"
    )

    memories = cursor.fetchall()
    conn.close()

    return memories


def delete_memory(memory_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

    conn.commit()
    conn.close()


initialize_database()
