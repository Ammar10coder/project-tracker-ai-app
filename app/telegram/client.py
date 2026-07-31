from telethon import TelegramClient

import paths
from app import config

# The single shared client instance used by the whole app while it's running.
# Created lazily (via get_client()) once Settings have been filled in, so
# importing this module never fails just because settings aren't set yet.
client: TelegramClient = None


def get_client() -> TelegramClient:
    global client
    cfg = config.load()
    api_id = int(cfg.get("API_ID") or 0)
    api_hash = cfg.get("API_HASH") or ""
    if not api_id or not api_hash:
        raise RuntimeError("Telegram API ID / API Hash are not set. Fill them in on the Settings tab first.")
    if client is None:
        client = TelegramClient(paths.SESSION_FILE, api_id, api_hash)
    return client


def reset_client():
    """Used if the user changes API ID/Hash in Settings and needs a fresh client."""
    global client
    client = None
