import sqlite3

import paths

DB_PATH = paths.DB_PATH


def init_db():
    from app.database import init_db as _init
    _init()


def reset_daily_chats():
    from app.database import reset_daily_chats as _reset
    _reset()


def fetch_all_user_activity_24h():
    """Fetches all tasks logged from ALL users across all chats, including progress metrics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COALESCE(sender_name, 'Unknown Employee') as sender_name,
            COALESCE(chat_name, 'General Chat') as chat_name,
            COALESCE(task_name, 'Untitled Task') as task_name,
            COALESCE(status, 'In Progress') as status,
            COALESCE(progress, 0) as progress,
            updated_at
        FROM tasks
        ORDER BY updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_update(user_name, update_date, raw_text, file_paths, status, ai_summary):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    file_str = ",".join(file_paths) if isinstance(file_paths, list) else str(file_paths)
    cursor.execute("""
        INSERT INTO daily_updates (user_name, update_date, raw_text, file_paths, status, ai_summary)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_name, update_date, raw_text, file_str, status, ai_summary))
    conn.commit()
    conn.close()


def get_last_update(user_name, current_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT raw_text, ai_summary FROM daily_updates
        WHERE user_name = ? AND update_date < ?
        ORDER BY update_date DESC LIMIT 1
    """, (user_name, current_date))
    row = cursor.fetchone()
    conn.close()
    return row


def get_last_reporter():
    """Returns the sender_name of whoever most recently had a task saved, or None."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT sender_name FROM tasks ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def save_task(sender_name, task_name, status, chat_name, progress=0):
    """Saves an AI-extracted task to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (sender_name, task_name, status, chat_name, progress)
        VALUES (?, ?, ?, ?, ?)
    """, (sender_name, task_name, status, chat_name, progress))
    conn.commit()
    conn.close()
    print(f"Saved task: {task_name} ({progress}%) for {sender_name}")


def save_message(telegram_message_id, sender, chat, message):
    """Saves incoming Telegram messages via SQLAlchemy ORM Session."""
    from app.database import SessionLocal
    from app.models import Message

    db = SessionLocal()
    try:
        new_message = Message(
            telegram_message_id=str(telegram_message_id),
            sender=sender,
            chat=chat,
            message=message,
        )
        db.add(new_message)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to save message: {e}")
        raise
    finally:
        db.close()
