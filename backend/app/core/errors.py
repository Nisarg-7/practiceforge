from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    429: "RATE_LIMITED",
    503: "SERVICE_UNAVAILABLE",
}


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Every HTTP error uses the contract format: {"error": {"code", "message"}}."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": _CODES.get(exc.status_code, "ERROR"),
                "message": str(exc.detail),
            }
        },
        headers=exc.headers,
    )