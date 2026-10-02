import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source_type TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    original_text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS explanations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    result_json TEXT NOT NULL,
    hindi_json TEXT,
    helpful INTEGER
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def save(source_type: str, doc_type: str, original_text: str, model: str, result: dict) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as c:
        cur = c.execute(
            "INSERT INTO documents (created_at, source_type, doc_type, original_text) VALUES (?,?,?,?)",
            (now, source_type, doc_type, original_text),
        )
        doc_id = cur.lastrowid
        c.execute(
            "INSERT INTO explanations (document_id, model, result_json) VALUES (?,?,?)",
            (doc_id, model, json.dumps(result, ensure_ascii=False)),
        )
        return doc_id


def list_documents() -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT d.id, d.created_at, d.doc_type, d.source_type, e.helpful, "
            "json_extract(e.result_json, '$.summary') AS summary "
            "FROM documents d JOIN explanations e ON e.document_id = d.id "
            "ORDER BY d.id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_document(doc_id: int) -> dict | None:
    with connect() as c:
        r = c.execute(
            "SELECT d.id, d.created_at, d.source_type, d.doc_type, d.original_text, "
            "e.model, e.result_json, e.hindi_json, e.helpful "
            "FROM documents d JOIN explanations e ON e.document_id = d.id WHERE d.id = ?",
            (doc_id,),
        ).fetchone()
    if not r:
        return None
    d = dict(r)
    d["result"] = json.loads(d.pop("result_json"))
    h = d.pop("hindi_json")
    d["hindi"] = json.loads(h) if h else None
    return d


def set_hindi(doc_id: int, hindi: dict) -> bool:
    with connect() as c:
        cur = c.execute(
            "UPDATE explanations SET hindi_json = ? WHERE document_id = ?",
            (json.dumps(hindi, ensure_ascii=False), doc_id),
        )
        return cur.rowcount > 0


def set_helpful(doc_id: int, helpful: bool) -> bool:
    with connect() as c:
        cur = c.execute(
            "UPDATE explanations SET helpful = ? WHERE document_id = ?",
            (1 if helpful else 0, doc_id),
        )
        return cur.rowcount > 0


def delete_document(doc_id: int) -> bool:
    with connect() as c:
        cur = c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        return cur.rowcount > 0