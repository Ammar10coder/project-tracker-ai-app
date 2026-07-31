import logging
from datetime import date
from app.database import SessionLocal
from app.models import Task, TaskHistory

logger = logging.getLogger(__name__)


def save_snapshot():
    """
    Captures the current state of active tasks from `Task` table
    and saves/updates them into `TaskHistory` under today's date.
    Must run BEFORE reset_daily_chats().
    """
    db = SessionLocal()
    today_str = str(date.today())

    try:
        tasks = db.query(Task).all()
        saved_count = 0

        for task in tasks:
            exists = db.query(TaskHistory).filter(
                TaskHistory.task_name == task.task_name,
                TaskHistory.sender_name == task.sender_name,
                TaskHistory.snapshot_date == today_str
            ).first()

            if exists:
                exists.status = task.status
                exists.progress = task.progress
            else:
                history = TaskHistory(
                    task_name=task.task_name,
                    status=task.status,
                    progress=task.progress,
                    sender_name=task.sender_name,
                    snapshot_date=today_str
                )
                db.add(history)

            saved_count += 1

        db.commit()
        logger.info(f"Saved/updated {saved_count} task snapshot(s) for {today_str}.")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save snapshot for {today_str}: {e}")
        raise e

    finally:
        db.close()
