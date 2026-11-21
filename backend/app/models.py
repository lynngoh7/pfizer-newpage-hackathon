"""Keep the Ollama models warm for the session, unload them when done.

Why: a cold model load takes several seconds, which makes the first search or
answer slow in the demo. So at startup we load nomic-embed-text and the answer
model with keep_alive=-1 (stay loaded), in a background thread so startup
never waits on Ollama.

Rules (brief §1a, §6):
  * No network: Ollama on 127.0.0.1 only.
  * No copies: unloading on quit and on "Forget everything" (session.on_forget)
    means the model holds nothing from the notes after we are done.
  * Warming sends no note text, only an empty request that loads the model.

Called by: main.main() via start(). Not imported by create_app, so tests never
talk to Ollama.
"""
from __future__ import annotations

import atexit
import json
import threading
import urllib.request

from . import prefs, session

OLLAMA = "http://127.0.0.1:11434"  # never configurable: local only
EMBED_MODEL = "nomic-embed-text"
DEFAULT_ANSWER_MODEL = "llama3.2:3b"


def answer_model() -> str:
    return prefs.load()["settings"].get("answer_model") or DEFAULT_ANSWER_MODEL


def _post(path: str, body: dict) -> None:
    req = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()


def _set(keep_alive) -> None:
    """keep_alive -1 loads and keeps a model; 0 unloads it. Errors are
    ignored: Ollama being off must never break startup, quit or forget."""
    for path, body in (("/api/embed", {"model": EMBED_MODEL, "input": ""}),
                       ("/api/generate", {"model": answer_model()})):
        try:
            _post(path, {**body, "keep_alive": keep_alive})
        except (OSError, ValueError):
            pass


def warm() -> None:
    threading.Thread(target=_set, args=(-1,), daemon=True, name="warm-models").start()


def unload() -> None:
    _set(0)


def start() -> None:
    warm()
    atexit.register(unload)       # quit
    session.on_forget("models", unload)  # Forget everything
