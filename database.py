"""
database.py - Persistent SQLite storage for Contexts and Conversations
Ensures 100% state persistence across serverless invocations (Vercel) and long-running servers (Render/Railway).
"""

import sqlite3
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "vera_state.db"))


def init_db():
    """Initialize SQLite tables for contexts and conversations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contexts (
        scope TEXT NOT NULL,
        context_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (scope, context_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_conv_id ON conversations (conversation_id)
    """)
    conn.commit()
    conn.close()


def save_context(scope: str, context_id: str, version: int, payload: dict) -> bool:
    """Save or update context payload with version check."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT version FROM contexts WHERE scope = ? AND context_id = ?", (scope, context_id))
    row = cursor.fetchone()

    if row and row[0] > version:
        conn.close()
        return False  # Stale version

    payload_str = json.dumps(payload, ensure_ascii=False)
    cursor.execute("""
    INSERT INTO contexts (scope, context_id, version, payload_json)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(scope, context_id) DO UPDATE SET
        version = excluded.version,
        payload_json = excluded.payload_json,
        updated_at = CURRENT_TIMESTAMP
    """, (scope, context_id, version, payload_str))

    conn.commit()
    conn.close()
    return True


def load_context(scope: str, context_id: str) -> Optional[dict]:
    """Retrieve context payload."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT payload_json FROM contexts WHERE scope = ? AND context_id = ?", (scope, context_id))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


def get_all_context_counts() -> Dict[str, int]:
    """Get counts of loaded contexts by scope."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT scope, COUNT(*) FROM contexts GROUP BY scope")
    rows = cursor.fetchall()
    conn.close()
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    for scope, count in rows:
        if scope in counts:
            counts[scope] = count
    return counts


def save_turn(conversation_id: str, role: str, message: str):
    """Save turn to conversation history."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conversations (conversation_id, role, message) VALUES (?, ?, ?)",
                   (conversation_id, role, message))
    conn.commit()
    conn.close()


def load_turns(conversation_id: str) -> List[Dict[str, Any]]:
    """Load conversation history for a given ID."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, message FROM conversations WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "message": r[1]} for r in rows]


def clear_all_data():
    """Wipe database for teardown."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contexts")
    cursor.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()
