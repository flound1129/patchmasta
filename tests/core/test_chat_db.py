import sqlite3
from pathlib import Path

from core.chat_db import ChatHistoryDB


def test_schema_tables(tmp_path):
    db = ChatHistoryDB(db_path=tmp_path / "test.db")
    cur = db._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cur.fetchall()]
    assert "conversations" in tables
    assert "messages" in tables
    db.close()


def test_add_conversation_returns_incrementing_ids(tmp_path):
    db = ChatHistoryDB(db_path=tmp_path / "test.db")
    id1 = db.add_conversation("claude")
    id2 = db.add_conversation("groq")
    assert id1 == 1
    assert id2 == 2
    db.close()


def test_add_conversation_stores_backend(tmp_path):
    db = ChatHistoryDB(db_path=tmp_path / "test.db")
    cid = db.add_conversation("groq")
    row = db._conn.execute(
        "SELECT backend FROM conversations WHERE id=?", (cid,)
    ).fetchone()
    assert row[0] == "groq"
    db.close()


def test_add_message_stores_and_retrieves(tmp_path):
    db = ChatHistoryDB(db_path=tmp_path / "test.db")
    cid = db.add_conversation("claude")
    mid = db.add_message(cid, "user", "Hello")
    row = db._conn.execute(
        "SELECT conversation_id, role, content, wav_path, tool_name"
        " FROM messages WHERE id=?",
        (mid,),
    ).fetchone()
    assert row == (cid, "user", "Hello", None, None)
    db.close()


def test_wav_path_column(tmp_path):
    db = ChatHistoryDB(db_path=tmp_path / "test.db")
    cid = db.add_conversation("claude")
    mid = db.add_message(cid, "user", "Match sound", wav_path="/tmp/test.wav")
    row = db._conn.execute(
        "SELECT wav_path FROM messages WHERE id=?", (mid,)
    ).fetchone()
    assert row[0] == "/tmp/test.wav"
    db.close()


def test_tool_name_column(tmp_path):
    db = ChatHistoryDB(db_path=tmp_path / "test.db")
    cid = db.add_conversation("claude")
    mid = db.add_message(cid, "tool", "result data", tool_name="set_parameter")
    row = db._conn.execute(
        "SELECT tool_name FROM messages WHERE id=?", (mid,)
    ).fetchone()
    assert row[0] == "set_parameter"
    db.close()


def test_default_path_uses_xdg_data():
    db = ChatHistoryDB()
    expected = Path.home() / ".local" / "share" / "patchmasta" / "chat_history.db"
    assert expected.exists()
    db.close()
    expected.unlink()


def test_creates_parent_dirs(tmp_path):
    deep = tmp_path / "a" / "b" / "c" / "test.db"
    db = ChatHistoryDB(db_path=deep)
    assert deep.exists()
    db.close()
