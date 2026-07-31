"""
App configuration.

Instead of a .env file (easy to lose/forget when moving between Windows
and Mac), all settings live in config/settings.json next to the app, and
are edited from the Settings tab of the dashboard in the browser.

Every value can also be overridden with an environment variable of the
same name if one is set (useful for advanced/CI use), but that's optional.
"""
import json
import os
import threading

import paths

_LOCK = threading.Lock()

DEFAULTS = {
    "API_ID": "",
    "API_HASH": "",
    "PHONE": "",
    "GEMINI_API_KEY": "",
    "GROQ_API_KEY": "",
    "OPENROUTER_API_KEY": "",
    "GMAIL_USER": "",
    "GMAIL_APP_PASSWORD": "",
    "REPORT_RECIPIENT_EMAIL": "",
    "TARGET_GROUP_NAME": "KELVIN6K WORK FLOW & UPDATES",
    "DRIVE_TARGET_FOLDER_ID": "",
    "DRIVE_COMPANY_NAME": "kelvin6k",
}

TEAM_ROLES = {
    "Ammar": "AI Engineer (Focus: Automation, LLM Pipelines, API Integrations, Reporting)",
}


def load() -> dict:
    with _LOCK:
        data = dict(DEFAULTS)
        if os.path.exists(paths.SETTINGS_FILE):
            try:
                with open(paths.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data.update(json.load(f))
            except Exception:
                pass
        # Environment variables win if explicitly set (optional power-user override).
        for key in DEFAULTS:
            env_val = os.getenv(key)
            if env_val:
                data[key] = env_val
        return data


def save(new_values: dict) -> dict:
    with _LOCK:
        current = {}
        if os.path.exists(paths.SETTINGS_FILE):
            try:
                with open(paths.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    current = json.load(f)
            except Exception:
                current = {}
        for key in DEFAULTS:
            if key in new_values:
                current[key] = new_values[key]
        os.makedirs(paths.CONFIG_DIR, exist_ok=True)
        with open(paths.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return load()


def is_configured() -> bool:
    cfg = load()
    required = ["API_ID", "API_HASH", "PHONE", "GEMINI_API_KEY"]
    return all(cfg.get(k) for k in required)


# Convenience module-level accessors used by other modules (refreshed on each call
# via get(), rather than cached at import time, so Settings-tab edits take effect
# without needing to fully restart the app).
def get(key: str, default=None):
    return load().get(key, default)
