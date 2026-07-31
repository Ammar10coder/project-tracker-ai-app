import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import paths

DB_PATH = paths.DB_PATH
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Ensures tables exist and migrates missing columns automatically."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT,
            status TEXT,
            progress INTEGER DEFAULT 0,
            sender_name TEXT,
            chat_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            sender_name TEXT,
            chat_name TEXT,
            raw_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            update_date TEXT NOT NULL,
            raw_text TEXT,
            file_paths TEXT,
            status TEXT,
            ai_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT,
            status TEXT,
            progress INTEGER,
            sender_name TEXT,
            snapshot_date TEXT
        );
    """)

    cursor.execute("PRAGMA table_info(tasks);")
    columns = [col[1] for col in cursor.fetchall()]

    if "task_name" not in columns:
        if "task" in columns:
            cursor.execute("ALTER TABLE tasks RENAME COLUMN task TO task_name;")
        elif "task_description" in columns:
            cursor.execute("ALTER TABLE tasks RENAME COLUMN task_description TO task_name;")
        else:
            cursor.execute("ALTER TABLE tasks ADD COLUMN task_name TEXT;")

    if "sender_name" not in columns:
        if "sender" in columns:
            cursor.execute("ALTER TABLE tasks RENAME COLUMN sender TO sender_name;")
        else:
            cursor.execute("ALTER TABLE tasks ADD COLUMN sender_name TEXT;")

    if "chat_name" not in columns:
        if "chat" in columns:
            cursor.execute("ALTER TABLE tasks RENAME COLUMN chat TO chat_name;")
        else:
            cursor.execute("ALTER TABLE tasks ADD COLUMN chat_name TEXT;")

    if "status" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN status TEXT;")

    if "progress" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN progress INTEGER DEFAULT 0;")

    if "created_at" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    if "updated_at" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    conn.commit()
    conn.close()


def reset_daily_chats():
    """Wipes old records after the daily report is dispatched."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages;")
    cursor.execute("DELETE FROM tasks;")
    conn.commit()
    conn.close()
    print("Database wiped: ready for the next 24-hour cycle.")


init_db()
