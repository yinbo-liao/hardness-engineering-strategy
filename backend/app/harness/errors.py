"""
RFC 7807 Problem Details error handling for the Harness API.
"""

from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse


def problem_detail(
    request: Request,
    type_uri: str,
    title: str,
    status_code: int,
    detail: str = "",
    instance: Optional[str] = None,
    extensions: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    body: Dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status_code,
        "detail": detail,
    }

    if instance is None:
        body["instance"] = str(request.url)

    if extensions:
        body.update(extensions)

    return JSONResponse(status_code=status_code, content=body)


def validation_error(request: Request, detail: str, errors: Optional[list] = None) -> JSONResponse:
    return problem_detail(
        request,
        type_uri="https://tools.ietf.org/html/rfc7231#section-6.5.1",
        title="Validation Error",
        status_code=400,
        detail=detail,
        extensions={"errors": errors} if errors else None,
    )


def not_found(request: Request, resource: str, resource_id: str = "") -> JSONResponse:
    return problem_detail(
        request,
        type_uri="https://tools.ietf.org/html/rfc7231#section-6.5.4",
        title="Not Found",
        status_code=404,
        detail=f"{resource} not found{f' (id: {resource_id})' if resource_id else ''}",
    )


def conflict(request: Request, detail: str) -> JSONResponse:
    return problem_detail(
        request,
        type_uri="https://tools.ietf.org/html/rfc7231#section-6.5.8",
        title="Conflict",
        status_code=409,
        detail=detail,
    )


def too_many_requests(request: Request, retry_after: int = 60) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "type": "https://tools.ietf.org/html/rfc7231#section-6.5.4",
            "title": "Too Many Requests",
            "status": 429,
            "detail": f"Rate limit exceeded. Retry after {retry_after} seconds.",
        },
        headers={"Retry-After": str(retry_after)},
    )


def unauthorized(request: Request, detail: str = "Authentication required") -> JSONResponse:
    return problem_detail(
        request,
        type_uri="https://tools.ietf.org/html/rfc7235#section-3.1",
        title="Unauthorized",
        status_code=401,
        detail=detail,
    )


def forbidden(request: Request, detail: str = "Insufficient permissions") -> JSONResponse:
    return problem_detail(
        request,
        type_uri="https://tools.ietf.org/html/rfc7231#section-6.5.3",
        title="Forbidden",
        status_code=403,
        detail=detail,
    )


def internal_error(request: Request, detail: str = "Internal server error") -> JSONResponse:
    return problem_detail(
        request,
        type_uri="https://tools.ietf.org/html/rfc7231#section-6.6.1",
        title="Internal Server Error",
        status_code=500,
        detail=detail,
    )
