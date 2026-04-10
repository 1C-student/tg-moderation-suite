from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "bot_data.sqlite3"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mutes (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                until_ts INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS limits (
                chat_id INTEGER PRIMARY KEY,
                messages_per_minute INTEGER NOT NULL
            )
            """
        )


def set_mute(chat_id: int, user_id: int, until_ts: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "REPLACE INTO mutes(chat_id, user_id, until_ts) VALUES (?, ?, ?)",
            (chat_id, user_id, until_ts),
        )


def delete_mute(chat_id: int, user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))


def get_limit(chat_id: int) -> int | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT messages_per_minute FROM limits WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        return row[0] if row else None


def set_limit(chat_id: int, messages_per_minute: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "REPLACE INTO limits(chat_id, messages_per_minute) VALUES (?, ?)",
            (chat_id, messages_per_minute),
        )
