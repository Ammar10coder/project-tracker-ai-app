from datetime import date, timedelta
from app.database import SessionLocal
from app.models import TaskHistory


def get_daily_comparison():
    """
    Compares today's task snapshot against yesterday's task snapshot
    using (sender_name, task_name) matching to classify task progress
    per employee.
    """
    db = SessionLocal()
    today_str = str(date.today())
    yesterday_str = str(date.today() - timedelta(days=1))

    today_rows = db.query(TaskHistory).filter(TaskHistory.snapshot_date == today_str).all()
    yesterday_rows = db.query(TaskHistory).filter(TaskHistory.snapshot_date == yesterday_str).all()

    yesterday_map = {
        (t.sender_name, t.task_name): {"status": t.status, "progress": t.progress or 0}
        for t in yesterday_rows
    }
    today_map = {
        (t.sender_name, t.task_name): {"status": t.status, "progress": t.progress or 0}
        for t in today_rows
    }

    all_keys = set(yesterday_map.keys()) | set(today_map.keys())
    report = []

    for key in all_keys:
        sender_name, title = key
        y = yesterday_map.get(key)
        t = today_map.get(key)

        if y is None:
            label = "New"
        elif t is None:
            label = "Removed"
        elif t["status"] and t["status"].lower() == "completed":
            label = "Completed"
        elif t["progress"] > y["progress"]:
            label = "Progressed"
        elif t["progress"] == y["progress"]:
            label = "Stalled"
        else:
            label = "Regressed"

        report.append({
            "title": title,
            "sender_name": sender_name or "Unknown Employee",
            "yesterday_progress": y["progress"] if y else 0,
            "today_progress": t["progress"] if t else 0,
            "status": t["status"] if t else "Removed",
            "label": label
        })

    db.close()
    return report
