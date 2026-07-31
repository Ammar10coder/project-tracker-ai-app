from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    telegram_message_id = Column(String)
    sender = Column(String)
    chat = Column(String)
    sender_name = Column(String)
    chat_name = Column(String)
    message = Column(Text)
    raw_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    task_name = Column(String)
    status = Column(String)
    progress = Column(Integer, default=0)
    sender_name = Column(String)
    chat_name = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True)
    report_date = Column(String)
    summary = Column(Text)
    overall_status = Column(String)
    deadline_risk = Column(String)


class TaskHistory(Base):
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True)
    task_name = Column(String)
    status = Column(String)
    progress = Column(Integer)
    sender_name = Column(String)
    snapshot_date = Column(String)
