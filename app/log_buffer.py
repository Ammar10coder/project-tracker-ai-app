import builtins
import collections
import datetime
import logging
import threading

_BUFFER = collections.deque(maxlen=2000)
_LOCK = threading.Lock()

_original_print = builtins.print


def _timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")


def add_line(line: str):
    with _LOCK:
        for part in str(line).splitlines() or [""]:
            _BUFFER.append(f"[{_timestamp()}] {part}")


def get_text() -> str:
    with _LOCK:
        return "\n".join(_BUFFER)


def _patched_print(*args, **kwargs):
    text = " ".join(str(a) for a in args)
    add_line(text)
    try:
        _original_print(*args, **kwargs)
    except Exception:
        pass


class BufferLogHandler(logging.Handler):
    def emit(self, record):
        try:
            add_line(self.format(record))
        except Exception:
            pass


def install():
    """Call once at app startup: routes all print()s and logging output into
    the shared buffer that the dashboard's Logs tab reads from."""
    builtins.print = _patched_print

    handler = BufferLogHandler()
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
