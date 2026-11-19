"""Session-token check applied to every request. Also marks every response
no-store so the webview never caches note text on disk."""
from __future__ import annotations

import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class SessionTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str):
        super().__init__(app)
        self._expected = token.encode()

    async def dispatch(self, request: Request, call_next):
        # CORS preflight carries no Authorization header; let CORSMiddleware answer it.
        if request.method == "OPTIONS":
            return await call_next(request)
        header = request.headers.get("authorization", "")
        scheme, _, presented = header.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(
            presented.encode(), self._expected
        ):
            return JSONResponse({"detail": "invalid or missing session token"}, status_code=401)
        response = await call_next(request)
        # No copies (brief §6): responses can carry note passages, so the
        # webview must never write them to its disk cache.
        response.headers["Cache-Control"] = "no-store"
        return response
