"""FastAPI routes. Every route lives under /api and is token-protected by the
middleware in auth.py, so handlers never check auth themselves.

Add new routes here per build step (or split into one router per module once
this grows). Keep handlers thin: validate, call a module function, return.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from . import __version__
from . import permissions
from . import models
from . import prefs
from . import search as search_mod
from . import qa

router = APIRouter(prefix="/api")


# Shown in Settings and polled by the sidebar dot. Fixed values on purpose:
# they state the app's promises, and the tests check they never change.
class Health(BaseModel):
    status: str = "ok"
    version: str = __version__
    read_only: bool = True
    network: str = "localhost-only"


class FolderAccess(BaseModel):
    paths: list[str]


class FolderAccessRequest(BaseModel):
    path: str = Field(min_length=1)


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health()


@router.get("/folders", response_model=FolderAccess)
def get_folders() -> FolderAccess: #return the paths the user has added
    return FolderAccess(paths=[str(path) for path in permissions.list_allowed_paths()])


@router.post("/folders", response_model=FolderAccess)
def add_folder(request: FolderAccessRequest) -> FolderAccess:
    try:
        permissions.grant_path(request.path) #try to add the path
    except FileNotFoundError as error: #if not exist
        raise HTTPException(status_code=404, detail="File or folder does not exist") from error
    except PermissionError as error: #if an api key or other non allowed
        raise HTTPException(status_code=403, detail=str(error)) from error
    except OSError as error: #if the OS doesn't allow it
        raise HTTPException(status_code=400, detail="Could not access the selected path") from error
    prefs.save_folders()  # paths only, never note content (One Rule)
    return FolderAccess(paths=[str(path) for path in permissions.list_allowed_paths()]) #return new allowed list


@router.delete("/folders", response_model=FolderAccess)
def remove_folder(path: str = Query(min_length=1)) -> FolderAccess:
    try:
        permissions.revoke_path(path) #try to remove path
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="File or folder does not exist") from error
    except OSError as error:
        raise HTTPException(status_code=400, detail="Could not access the selected path") from error
    prefs.save_folders()
    return FolderAccess(paths=[str(allowed) for allowed in permissions.list_allowed_paths()]) #return new allowed list


class SavedSettings(BaseModel):
    answer_model: str | None = None


class AskRequest(BaseModel):
    """Question submitted by the manager."""

    # Only accept the question, not arbitrary note contents.
    question: str = Field(min_length=1, max_length=500)


class AskCitation(BaseModel):
    """A verified quotation from a retrieved note."""

    chunk_id: int
    quote: str
    start: int
    end: int


class AskClaim(BaseModel):
    """An AI-generated claim with verified citations."""

    text: str
    citations: list[AskCitation]


class AskResponse(BaseModel):
    """Structured response returned to the frontend."""

    status: str
    supported: bool
    answer: str | None
    message: str | None
    claims: list[AskClaim]
    sources: list[dict]


@router.get("/settings", response_model=SavedSettings)
def get_settings() -> SavedSettings:
    return SavedSettings(**prefs.load()["settings"])


@router.put("/settings", response_model=SavedSettings)
def put_settings(request: SavedSettings) -> SavedSettings:
    # prefs drops any key not on its allowlist, so only setting values reach disk.
    return SavedSettings(**prefs.save_settings(request.model_dump(exclude_none=True)))


@router.post("/engine/unload")
def unload_model() -> dict:
    """Launcher calls this on quit, before stopping the backend."""
    return {"unloaded": models.unload()}


@router.post("/index")
def build_index() -> dict:
    """Re-read the allowed folders into the in-memory index."""
    return search_mod.reindex()


@router.get("/index")
def index_stats() -> dict:
    """Counts plus build progress; the UI polls this while meaning search builds."""
    return {**search_mod.db.stats(), **search_mod.status()}


@router.get("/search")
def search(q: str = Query(min_length=1, max_length=500)) -> dict:
    return search_mod.search(q)


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Answer questions using locally stored, permitted notes."""

    # Search notes that the user has permitted the app to access.
    search_result = search_mod.search(request.question)

    # Convert search results into the structure expected by qa.py.
    chunks = {
        str(source["chunkID"]): source["snippet"]
        for source in search_result["sources"]
    }

    try:
        # Generate an answer and validate its citations.
        result = qa.ask_question(request.question, chunks)

    except qa.QAError as error:
        # Report inference failure without exposing note contents.
        raise HTTPException(
            status_code=503,
            detail="Local AI inference is unavailable",
        ) from error

    # Convert validated claims into API response objects.
    claims = [
        AskClaim(
            text=claim.text,
            citations=[
                AskCitation(
                    chunk_id=int(citation.chunk_id),
                    quote=citation.quote,
                    start=citation.start,
                    end=citation.end,
                )
                for citation in claim.citations
            ],
        )
        for claim in result.claims
    ]

    # Identify which source cards support accepted claims.
    cited_ids = {
        citation.chunk_id
        for claim in claims
        for citation in claim.citations
    }

    # Return source cards only for cited excerpts.
    sources = [
        source
        for source in search_result["sources"]
        if source["chunkID"] in cited_ids
    ]

    return AskResponse(
        status="ok" if result.supported else "no_support",
        supported=result.supported,
        answer=(
            "\n".join(claim.text for claim in claims)
            if result.supported else None
        ),
        message=result.message,
        claims=claims,
        sources=sources,
    )

