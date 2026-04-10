import time
from typing import Any

import structlog
from asgi_correlation_id import correlation_id
from starlette.types import ASGIApp, Receive, Scope, Send
from uvicorn.protocols.utils import get_path_with_query_string

from app.core.config import settings


def _access_logger() -> Any:
    return structlog.get_logger(settings.log_access_logger_name)


class StructLogMiddleware:
    """Bind request context for structlog and emit one structured access log per HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        structlog.contextvars.clear_contextvars()
        rid = correlation_id.get()
        client = scope.get("client")
        client_host = client[0] if client else None
        client_port = client[1] if client else None

        structlog.contextvars.bind_contextvars(
            request_id=rid,
            http_method=scope["method"],
            http_path=scope["path"],
        )

        info: dict[str, Any] = {}

        async def inner_send(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                info["status_code"] = message["status"]
            await send(message)

        start = time.perf_counter()
        try:
            await self.app(scope, receive, inner_send)
        except Exception:
            structlog.get_logger().exception(
                "unhandled_exception_in_request",
                exc_info=True,
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            status_code = int(info.get("status_code", 500))
            url = get_path_with_query_string(scope)
            _access_logger().info(
                "http_access",
                request_id=rid,
                http_method=scope["method"],
                url=str(url),
                status_code=status_code,
                client_host=client_host,
                client_port=client_port,
                duration_ms=round(duration_ms, 3),
            )
