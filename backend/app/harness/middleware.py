import asyncio
import time
from collections import defaultdict
from typing import Callable, Optional

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.app.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiting middleware.

    Tracks requests per client IP within a configurable window.
    Rejects with HTTP 429 when the limit is exceeded.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._counters: dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self.window_seconds

        requests = [t for t in self._counters[client_ip] if t > window_start]
        self._counters[client_ip] = requests

        if len(requests) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "type": "https://tools.ietf.org/html/rfc7231#section-6.5.4",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds}s.",
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        self._counters[client_ip].append(now)
        return await call_next(request)


class RBACMiddleware(BaseHTTPMiddleware):
    """
    JWT-based Role-Based Access Control middleware.

    Validates Bearer tokens and extracts permission levels.
    Attaches user context to request.state for downstream use.
    """

    def __init__(self, app, exempt_paths: Optional[set] = None):
        super().__init__(app)
        settings = get_settings()
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.exempt_paths = exempt_paths or {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/harness/ws/main",
        }

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        if request.url.path.startswith("/ws"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            if request.method == "OPTIONS":
                return await call_next(request)
            return JSONResponse(
                status_code=401,
                content={
                    "type": "https://tools.ietf.org/html/rfc7235#section-3.1",
                    "title": "Unauthorized",
                    "status": 401,
                    "detail": "Missing or invalid Authorization header. Expected: Bearer <token>",
                },
            )

        token = auth_header[7:]
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            request.state.user = {
                "sub": payload.get("sub", "unknown"),
                "permission": payload.get("permission", "READ"),
                "roles": payload.get("roles", []),
            }
        except JWTError:
            return JSONResponse(
                status_code=401,
                content={
                    "type": "https://tools.ietf.org/html/rfc7235#section-3.1",
                    "title": "Unauthorized",
                    "status": 401,
                    "detail": "Invalid or expired token",
                },
            )

        return await call_next(request)


def require_permission(min_permission: str) -> Callable:
    """
    Decorator for endpoint-level permission checks.

    Usage:
        @router.post("/dangerous")
        @require_permission("ADMIN")
        async def admin_endpoint(request: Request):
            ...
    """
    permission_levels = {"READ": 1, "WRITE": 2, "EXECUTE": 3, "DEPLOY": 4, "ADMIN": 5}

    def decorator(handler: Callable) -> Callable:
        async def wrapper(request: Request, *args, **kwargs):
            user = getattr(request.state, "user", None)
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")

            user_level = permission_levels.get(user.get("permission", "READ"), 0)
            required_level = permission_levels.get(min_permission, 5)

            if user_level < required_level:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Permission denied. Required: {min_permission}, "
                        f"You have: {user.get('permission', 'READ')}"
                    ),
                )

            return await handler(request, *args, **kwargs)

        return wrapper

    return decorator
