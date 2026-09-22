"""ASGI body guard that rejects oversized uploads before buffering them."""

from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, limit=65536):
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or not scope.get("path", "").startswith("/api/")
            or scope.get("method") not in {"POST", "PUT", "PATCH", "DELETE"}
        ):
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                declared = int(content_length)
            except ValueError:
                return await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(
                    scope, receive, send
                )
            if declared < 0:
                return await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(
                    scope, receive, send
                )
            if declared > self.limit:
                return await JSONResponse(
                    {"detail": "Request body exceeds 64 KB."}, status_code=413
                )(scope, receive, send)
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > self.limit:
                return await JSONResponse(
                    {"detail": "Request body exceeds 64 KB."}, status_code=413
                )(scope, receive, send)
            chunks.append(body)
            if not message.get("more_body", False):
                break
        consumed = False

        async def buffered_receive():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, buffered_receive, send)
