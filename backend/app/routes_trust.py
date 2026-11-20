"""Trust panel routes (build step 5). Token-protected by the middleware like
every other route. Kept apart from api.py so step 2-4 route work does not clash.

  GET    /api/audit?after=N   activity log entries newer than N
  GET    /api/trust/network   app processes and their sockets
  GET    /api/trust/saved     the saved folder list and settings (prefs.json)
  GET    /api/trust/storage   what the app has on disk right now
  DELETE /api/session         forget everything
"""
from __future__ import annotations

from fastapi import APIRouter

from . import audit, prefs, session, trust

router = APIRouter(prefix="/api")


@router.get("/audit")
def get_audit(after: int = 0) -> list[dict]:
    # The Privacy page passes the last seq it has, so each poll is tiny.
    return audit.entries(after)


@router.get("/trust/network")
def get_network() -> dict:
    return trust.network()


@router.get("/trust/saved")
def get_saved() -> dict:
    # Exactly what prefs.json holds, so the user can read it on the Privacy page.
    return {"path": str(prefs.path()), "exists": prefs.path().exists(), **prefs.load()}


@router.get("/trust/storage")
def get_storage() -> dict:
    return trust.storage()


@router.delete("/session")
def delete_session() -> dict:
    # Re-check the disk straight away so the UI can show proof, not a promise.
    return {"cleared": session.forget(), "storage": trust.storage()}
