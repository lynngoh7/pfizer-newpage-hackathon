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

Called by: main.main() via start() (warm + unload at exit). api.py imports it
for POST /api/engine/unload, which the launcher calls on quit. The forget hook
is registered on import. This is the one place that unloads models: any new
model (e.g. qa.py's) must be listed in _ours().
"""
from __future__ import annotations

import atexit
import json
import threading
import urllib.request

from . import group, prefs, session

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


def _ours() -> list[str]:
    return list(dict.fromkeys((EMBED_MODEL, group.NAME_MODEL, answer_model())))


def _warm() -> None:
    """keep_alive -1 loads and keeps a model. Errors are ignored: Ollama being
    off must never break startup."""
    for path, body in (("/api/embed", {"model": EMBED_MODEL, "input": ""}),
                       ("/api/generate", {"model": answer_model()})):
        try:
            _post(path, {**body, "keep_alive": -1})
        except (OSError, ValueError):
            pass


def warm() -> None:
    threading.Thread(target=_warm, daemon=True, name="warm-models").start()


def unload() -> int:
    """Tell Ollama to drop our models now (keep_alive 0), so it holds no
    context once the session ends (One Rule: no copies). Asks /api/ps first so
    it never loads a model just to unload it. Returns how many it unloaded."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/ps", timeout=2) as r:
            loaded = {m["name"] for m in json.loads(r.read()).get("models", [])}
    except (OSError, ValueError):
        return 0  # Ollama not running: nothing is loaded
    n = 0
    for model in _ours():
        if not any(name.split(":")[0] == model.split(":")[0] and
                   (":" not in model or name == model) for name in loaded):
            continue
        path = "/api/embed" if model == EMBED_MODEL else "/api/generate"
        try:
            _post(path, {"model": model, "keep_alive": 0})
            n += 1
        except (OSError, ValueError):
            pass
    return n


def start() -> None:
    warm()
    atexit.register(unload)  # quit, if the launcher's unload call was missed


session.on_forget("model", unload)  # Forget everything
