"""
Central place that decides WHERE on disk this app reads/writes its data.

Goal: the app is fully portable. Whether it's:
  - run directly with `python app_main.py` while developing, or
  - double-clicked as ProjectTrackerAI.exe (Windows) / the extracted
    Mac build after PyInstaller packages it,

...it always keeps its database, Telegram session, Google credentials,
generated PDF reports and settings in a "data" folder that sits right
next to the app, so it survives restarts and is easy to back up or move.

Nothing here ever writes inside the PyInstaller temp extraction dir
(sys._MEIPASS), which is read-only/temporary — only next to the real
executable.
"""
import os
import sys


def get_base_dir() -> str:
    """Folder the executable / script lives in (NOT the PyInstaller temp dir)."""
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller-built exe/binary.
        return os.path.dirname(os.path.abspath(sys.executable))
    # Running as a normal Python script.
    return os.path.dirname(os.path.abspath(__file__))


def get_bundle_dir() -> str:
    """Folder that read-only bundled resources (web assets, default client_secrets) live in."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
BUNDLE_DIR = get_bundle_dir()

DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

WEB_DIR = os.path.join(BUNDLE_DIR, "web")

DB_PATH = os.path.join(DATA_DIR, "project.db")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
SESSION_FILE = os.path.join(DATA_DIR, "project_tracker_session")  # telethon appends .session
DRIVE_CREDS_FILE = os.path.join(DATA_DIR, "mycreds.txt")
CLIENT_SECRETS_FILE = os.path.join(CONFIG_DIR, "client_secrets.json")
CLIENT_SECRETS_DEFAULT = os.path.join(BUNDLE_DIR, "client_secrets", "client_secrets.json")
LOG_FILE = os.path.join(LOGS_DIR, "app.log")


def ensure_dirs():
    for d in (DATA_DIR, CONFIG_DIR, REPORTS_DIR, LOGS_DIR):
        os.makedirs(d, exist_ok=True)


ensure_dirs()
