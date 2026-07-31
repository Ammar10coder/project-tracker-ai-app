import asyncio
import threading
import traceback

from telethon import events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError

from app import config

TARGET_GROUP_NAME_DEFAULT = "KELVIN6K WORK FLOW & UPDATES"

_lock = threading.Lock()
_thread: threading.Thread = None
_loop: asyncio.AbstractEventLoop = None

state = {
    "running": False,       # listener fully connected & live
    "starting": False,      # start button pressed, still connecting/logging in
    "stage": None,          # None | 'need_phone' | 'need_code' | 'need_password'
    "error": None,
    "last_message": None,
}

_login = {"phone": None, "code": None, "password": None}


# ---------------------------------------------------------------------
# Public controls (safe to call from the web server thread)
# ---------------------------------------------------------------------
def is_running() -> bool:
    return state["running"] or state["starting"]


def start():
    global _thread
    with _lock:
        if is_running():
            return {"ok": False, "message": "Already running."}
        state.update(running=False, starting=True, stage=None, error=None)
        _login.update(phone=None, code=None, password=None)
        _thread = threading.Thread(target=_thread_main, daemon=True)
        _thread.start()
    return {"ok": True, "message": "Starting..."}


def stop():
    global _loop
    if not is_running():
        return {"ok": False, "message": "Not running."}
    if _loop is not None:
        try:
            _loop.call_soon_threadsafe(_request_stop)
        except Exception:
            pass
    return {"ok": True, "message": "Stopping..."}


def submit_phone(phone: str):
    _login["phone"] = phone.strip()


def submit_code(code: str):
    _login["code"] = code.strip()


def submit_password(password: str):
    _login["password"] = password


# ---------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------
def _request_stop():
    from app.telegram.client import client
    if client and client.is_connected():
        asyncio.ensure_future(client.disconnect())


def _thread_main():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    try:
        _loop.run_until_complete(_async_main())
    except Exception as e:
        state["error"] = str(e)
        print(f"Worker crashed: {e}")
        print(traceback.format_exc())
    finally:
        state["running"] = False
        state["starting"] = False
        state["stage"] = None
        try:
            _loop.close()
        except Exception:
            pass


async def _async_main():
    from app.telegram.client import get_client, reset_client
    reset_client()
    client = get_client()

    await client.connect()

    if not await client.is_user_authorized():
        await _login_flow(client)

    if not await client.is_user_authorized():
        state["error"] = "Telegram login was not completed."
        return

    _register_handlers(client)
    _start_scheduler()

    state["starting"] = False
    state["running"] = True
    state["stage"] = None
    print("Listener running. Waiting for messages...")

    await client.run_until_disconnected()


async def _login_flow(client):
    cfg = config.load()
    phone = cfg.get("PHONE")

    if not phone:
        state["stage"] = "need_phone"
        while not _login["phone"]:
            await asyncio.sleep(0.4)
        phone = _login["phone"]
        config.save({"PHONE": phone})

    sent = await client.send_code_request(phone)
    phone_code_hash = sent.phone_code_hash

    while True:
        state["stage"] = "need_code"
        state["error"] = None
        while not _login["code"]:
            await asyncio.sleep(0.4)
        code = _login["code"]
        _login["code"] = None

        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            break
        except SessionPasswordNeededError:
            state["stage"] = "need_password"
            state["error"] = None
            while not _login["password"]:
                await asyncio.sleep(0.4)
            password = _login["password"]
            _login["password"] = None
            try:
                await client.sign_in(password=password)
                break
            except Exception as e:
                state["error"] = f"Password rejected: {e}"
                continue
        except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
            state["error"] = f"That code didn't work ({e}). Request a new one and try again."
            continue
        except Exception as e:
            state["error"] = f"Login failed: {e}"
            continue

    state["stage"] = None
    state["error"] = None


def _register_handlers(client):
    from telethon.tl.types import User, Channel, Chat
    from app.services.daily_pdf_service import build_and_send_24h_pdf_report
    from app.services.history_service import save_snapshot
    from app.services.database_service import save_task, get_last_reporter, reset_daily_chats
    from app.services.ai_service import analyze_message

    def process_update(msg_id, sender_name, chat_name, text):
        print(f"Analyzing message from '{sender_name}': \"{text}\"")
        try:
            res = analyze_message(text)
            extracted_tasks = res.get("tasks", []) if isinstance(res, dict) else []

            if not extracted_tasks:
                clean_text = text.strip().strip('"').strip("'")
                extracted_tasks = [{
                    "task_title": clean_text[:80] if clean_text else "Daily Status Update",
                    "status": "In Progress",
                    "progress_percentage": 50
                }]

            for task in extracted_tasks:
                task_title = task.get("task_title") or task.get("task_name") or "Daily Task Update"
                task_status = task.get("status", "In Progress")
                task_progress = task.get("progress_percentage", 50)
                save_task(sender_name, task_title, task_status, chat_name, task_progress)

        except Exception as e:
            print(f"Error in process_update: {e}")
            save_task(sender_name, text.strip()[:80], "In Progress", chat_name, 50)

    async def resolve_sender_name(event):
        sender = await event.get_sender()
        if not sender and event.sender_id:
            try:
                sender = await event.client.get_entity(event.sender_id)
            except Exception:
                sender = None

        sender_name = "Unknown Employee"
        if sender:
            if isinstance(sender, User):
                full_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                if full_name:
                    sender_name = full_name
            elif isinstance(sender, (Channel, Chat)):
                sender_name = getattr(sender, "title", "Unknown Group")
        return sender_name

    @client.on(events.NewMessage)
    async def message_handler(event):
        cfg = config.load()
        target_group_name = cfg.get("TARGET_GROUP_NAME") or TARGET_GROUP_NAME_DEFAULT

        if event.raw_text and event.raw_text.strip().lower() == "/report_now":
            requester_name = await resolve_sender_name(event)
            print(f"Manual /report_now requested by [{requester_name}]")
            await asyncio.to_thread(save_snapshot)
            target_name = await asyncio.to_thread(get_last_reporter)
            if not target_name:
                await event.reply("No reported updates found yet - nothing to generate a report for.")
                return
            await asyncio.to_thread(build_and_send_24h_pdf_report, target_name)
            await event.reply(f"Report for [{target_name}] generated and saved successfully!")
            return

        chat = await event.get_chat()
        chat_name = getattr(chat, "title", "Private Chat")
        if target_group_name.lower() not in chat_name.lower():
            return

        sender_name = await resolve_sender_name(event)
        print(f"Received message from [{sender_name}] in [{chat_name}]")
        state["last_message"] = f"{sender_name}: {event.raw_text[:60] if event.raw_text else ''}"

        await asyncio.to_thread(process_update, event.id, sender_name, chat_name, event.raw_text or "")


def _start_scheduler():
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app.services.daily_pdf_service import build_and_send_24h_pdf_report
    from app.services.history_service import save_snapshot
    from app.services.database_service import reset_daily_chats

    async def run_daily_nightly_job():
        print("9:00 PM reached. Running nightly report pipeline...")
        await asyncio.to_thread(save_snapshot)
        await asyncio.to_thread(build_and_send_24h_pdf_report)
        await asyncio.to_thread(reset_daily_chats)
        print("Nightly job completed.")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_nightly_job, 'cron', hour=21, minute=0)
    scheduler.start()
