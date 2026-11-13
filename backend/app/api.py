"""FastAPI routes. Every route lives under /api and is token-protected by the
middleware in auth.py, so handlers never check auth themselves.

Add new routes here per build step (or split into one router per module once
this grows). Keep handlers thin: validate, call a module function, return.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from . import __version__

router = APIRouter(prefix="/api")


class Health(BaseModel):
    status: str = "ok"
    version: str = __version__
    read_only: bool = True
    network: str = "localhost-only"


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health()
