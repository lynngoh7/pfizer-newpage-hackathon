"""ASGI app factory and sidecar entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .auth import SessionTokenMiddleware
from .config import HOST, Settings, load_settings

# Origins allowed to call the backend. The packaged desktop app only accepts the
# Tauri window. The Vite dev server is added only when NOTES_DEV=1 (set by
# scripts/dev.sh and by the Rust launcher in debug builds). Rule §6 "no network".
APP_ORIGINS = [
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
]
DEV_ORIGINS = [
    "http://127.0.0.1:1420",
    "http://localhost:1420",
]


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Local Notes Assistant", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    # Order matters: Starlette applies the last-added middleware first, so CORS
    # wraps auth and can answer preflights before the token check runs.
    app.add_middleware(SessionTokenMiddleware, token=settings.session_token)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=APP_ORIGINS + (DEV_ORIGINS if settings.dev else []),
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(router)
    return app


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(create_app(settings), host=HOST, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
