#!/usr/bin/env python3
"""
Project Tracker AI — standalone desktop app.

No Docker, no separate server to run. This single process:
  - serves a local dashboard in your browser (http://127.0.0.1:8765)
  - starts/stops the Telegram listener + nightly report job on your click
  - walks you through Telegram login and Google Drive login from the browser

Everything (Python interpreter + all pip packages) is bundled in when this
is built with PyInstaller, so end users don't need Python installed.
"""
import json
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import paths
from app import log_buffer

log_buffer.install()

import worker
from app import config

PORT = 8765

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


def _drive_status():
    try:
        from app.services.drive_service import is_drive_connected
        return is_drive_connected()
    except Exception:
        return False


def _build_status():
    return {
        "configured": config.is_configured(),
        "running": worker.state["running"],
        "starting": worker.state["starting"],
        "stage": worker.state["stage"],
        "error": worker.state["error"],
        "last_message": worker.state["last_message"],
        "drive_connected": _drive_status(),
    }


def _connect_drive_async():
    def _run():
        try:
            from app.services.drive_service import DriveManager
            DriveManager()
            print("Google Drive connected successfully.")
        except Exception as e:
            print(f"Google Drive connection failed: {e}")
    threading.Thread(target=_run, daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._send_json({"error": "not found"}, 404)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_file(os.path.join(paths.WEB_DIR, "index.html"), CONTENT_TYPES[".html"])
        elif self.path == "/app.js":
            self._send_file(os.path.join(paths.WEB_DIR, "app.js"), CONTENT_TYPES[".js"])
        elif self.path == "/style.css":
            self._send_file(os.path.join(paths.WEB_DIR, "style.css"), CONTENT_TYPES[".css"])
        elif self.path == "/api/status":
            self._send_json(_build_status())
        elif self.path == "/api/settings":
            self._send_json(config.load())
        elif self.path.startswith("/api/logs"):
            self._send_json({"logs": log_buffer.get_text()})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/start":
            self._send_json(worker.start())
        elif self.path == "/api/stop":
            self._send_json(worker.stop())
        elif self.path == "/api/settings":
            body = self._read_json_body()
            config.save(body)
            self._send_json({"ok": True, "message": "Saved."})
        elif self.path == "/api/telegram/phone":
            body = self._read_json_body()
            worker.submit_phone(body.get("value", ""))
            self._send_json({"ok": True})
        elif self.path == "/api/telegram/code":
            body = self._read_json_body()
            worker.submit_code(body.get("value", ""))
            self._send_json({"ok": True})
        elif self.path == "/api/telegram/password":
            body = self._read_json_body()
            worker.submit_password(body.get("value", ""))
            self._send_json({"ok": True})
        elif self.path == "/api/drive/connect":
            _connect_drive_async()
            self._send_json({"ok": True, "message": "Opening your browser for Google sign-in..."})
        else:
            self._send_json({"error": "not found"}, 404)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"Project Tracker AI dashboard running at {url}")

    def _open_browser():
        time.sleep(0.6)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
