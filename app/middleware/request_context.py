from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in chain is the original client.
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Adds a stable per-request request_id for correlation and audit logging.
    If the caller provides X-Request-Id, we reuse it (up to a reasonable length).
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id")
        request_id = (incoming or str(uuid4()))[:64]
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

