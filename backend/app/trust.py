"""Trust checks: lets the user see for themselves that nothing left or stayed.

Answers the brief's "How would you know?" (§1a, Trust panel):
  * network(): every open socket of the app's own processes (this backend, the
    desktop app that launched it, and Ollama), each marked listening, local or
    external. Anything external is a red flag in the UI.
  * storage(): the places a desktop app would normally write data, with what
    is in them right now. Expected: only prefs.json (folder paths + settings,
    see prefs.py). Any other file is reported as unexpected.

Read-only: inspects, never changes anything. Called by routes_trust.py.
"""
from __future__ import annotations

import ipaddress
import os
import sys
from pathlib import Path

import psutil

APP_ID = "local.notes.assistant"  # must match "identifier" in src-tauri/tauri.conf.json
# The webview (WebKit on macOS) names its folders after the binary instead,
# i.e. the package name in src-tauri/Cargo.toml.
BIN_NAME = "local-notes-assistant"
MAX_LISTED_FILES = 20


def _kind(remote) -> str:
    if not remote:
        return "listening"
    try:
        # Loopback (127.x, ::1) never leaves the machine. Anything else does,
        # including LAN addresses like 192.168.x: those still leave the device.
        return "local" if ipaddress.ip_address(remote.ip).is_loopback else "external"
    except ValueError:
        return "external"  # unknown address format: assume the worst


def _our_processes() -> list[tuple[str, psutil.Process]]:
    """(role, process) for this backend, the app that launched it, and Ollama."""
    me = psutil.Process()
    procs = [("engine", me)]
    parent = me.parent()
    # pid 1 is the OS itself (we were orphaned), not our app.
    if parent is not None and parent.pid > 1:
        procs.append(("app", parent))  # the desktop app (or the dev script during development)
    for p in psutil.process_iter(["name"]):
        if (p.info["name"] or "").lower().startswith("ollama") and p.pid != me.pid:
            procs.append(("model", p))
    return procs


def network() -> dict:
    processes, external = [], 0
    for role, p in _our_processes():
        entry = {"role": role, "pid": p.pid, "name": "", "connections": [], "error": None}
        try:
            entry["name"] = p.name()
            for c in p.net_connections(kind="inet"):
                kind = _kind(c.raddr)
                external += kind == "external"
                entry["connections"].append({
                    "local": f"{c.laddr.ip}:{c.laddr.port}",
                    "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None,
                    "kind": kind,
                })
        except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
            entry["error"] = type(e).__name__
        processes.append(entry)
    return {"external": external, "processes": processes}


def _app_dirs() -> list[Path]:
    home = Path.home()
    if sys.platform == "darwin":
        lib = home / "Library"
        return [lib / sub / name
                for sub in ("Application Support", "Caches", "Logs", "WebKit", "HTTPStorages")
                for name in (APP_ID, BIN_NAME)] + [
                lib / "Preferences" / f"{APP_ID}.plist",
                lib / "Saved Application State" / f"{APP_ID}.savedState"]
    if sys.platform == "win32":
        return [Path(os.environ.get(v, home)) / n for v in ("APPDATA", "LOCALAPPDATA") for n in (APP_ID, BIN_NAME)]
    return [home / d / n for d in (".local/share", ".config", ".cache") for n in (APP_ID, BIN_NAME)]


def storage() -> dict:
    from . import prefs  # late import: prefs imports session, keep trust import-light

    saved = prefs.path().resolve()
    locations, total = [], 0
    for path in _app_dirs():
        # Each location is a folder, a single file (e.g. a .plist), or absent.
        if path.is_dir():
            files = sorted(f for f in path.rglob("*") if f.is_file())
        elif path.is_file():
            files = [path]
        else:
            files = []
        files = [f for f in files if f.resolve() != saved]  # the one expected file
        # Windows: WebView2 keeps the window's own browser profile (EBWebView).
        # Expected, and holds no notes: every API reply is no-store (auth.py).
        engine = [f for f in files if "EBWebView" in f.relative_to(path).parts[:1]]
        files = [f for f in files if f not in engine]
        total += len(files)
        locations.append({
            "path": str(path),
            "exists": path.exists(),
            "files": len(files),
            "engine": len(engine),
            "bytes": sum(f.stat().st_size for f in files),
            "listed": [str(f.relative_to(path)) if f != path else f.name for f in files[:MAX_LISTED_FILES]],
        })
    return {"files": total, "locations": locations,
            "saved": {"path": str(saved), "bytes": saved.stat().st_size if saved.exists() else 0}}
