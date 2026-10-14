"""SQLite: схема, сохранения, лог LLM-запросов."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS translation_cache (
    key TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    source_lang TEXT,
    target_lang TEXT
);
CREATE TABLE IF NOT EXISTS saves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    snapshot TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS undo_stack (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content_en TEXT,
    content_ru TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request TEXT NOT NULL,
    response TEXT,
    ok INTEGER DEFAULT 1,
    created_at REAL NOT NULL
);
"""


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.executescript(SCHEMA)


def save_snapshot(db_path: str, name: str, state_dict: dict[str, Any]) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT OR REPLACE INTO saves(name, snapshot, created_at) VALUES (?,?,?)",
            (name, json.dumps(state_dict, ensure_ascii=False), time.time()),
        )


def load_snapshot(db_path: str, name: str) -> dict[str, Any] | None:
    with sqlite3.connect(db_path) as con:
        row = con.execute("SELECT snapshot FROM saves WHERE name=?", (name,)).fetchone()
    return json.loads(row[0]) if row else None


def list_saves(db_path: str) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as con:
        rows = con.execute("SELECT name, created_at FROM saves ORDER BY created_at DESC").fetchall()
    return [{"name": r[0], "created_at": r[1]} for r in rows]


def push_undo(db_path: str, state_dict: dict[str, Any]) -> None:
    """Снапшот перед ходом — для undo последнего хода."""
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO undo_stack(snapshot, created_at) VALUES (?,?)",
                    (json.dumps(state_dict, ensure_ascii=False), time.time()))
        con.execute("""DELETE FROM undo_stack WHERE id NOT IN
                       (SELECT id FROM undo_stack ORDER BY id DESC LIMIT 50)""")


def pop_undo(db_path: str) -> dict[str, Any] | None:
    with sqlite3.connect(db_path) as con:
        row = con.execute("SELECT id, snapshot FROM undo_stack ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        con.execute("DELETE FROM undo_stack WHERE id=?", (row[0],))
    return json.loads(row[1])


def log_llm(db_path: str, request: dict[str, Any], response: str | None, ok: bool) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT INTO llm_log(request, response, ok, created_at) VALUES (?,?,?,?)",
            (json.dumps(request, ensure_ascii=False), response, int(ok), time.time()),
        )
