import asyncio

from hawkerbridge.middleware import BodyLimitMiddleware


def run_body(chunks, content_length=None):
    received = []
    sent = []
    calls = []

    async def application(scope, receive, send):
        calls.append(True)
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    pending = iter(chunks)

    async def receive():
        value = next(pending)
        received.append(value)
        return value

    async def send(value):
        sent.append(value)

    headers = [] if content_length is None else [(b"content-length", str(content_length).encode())]
    scope = {"type": "http", "path": "/api/plans", "method": "POST", "headers": headers}
    asyncio.run(BodyLimitMiddleware(application, limit=10)(scope, receive, send))
    return received, sent, calls


def test_rejects_large_declared_length_before_read():
    received, sent, calls = run_body([], 100)
    assert not received and not calls
    assert sent[0]["status"] == 413


def test_chunked_body_stops_reading_as_soon_as_limit_exceeded():
    data = [
        {"type": "http.request", "body": b"123456", "more_body": True},
        {"type": "http.request", "body": b"123456", "more_body": True},
        {"type": "http.request", "body": b"MUST NOT BE READ", "more_body": False},
    ]
    received, sent, calls = run_body(data)
    assert len(received) == 2 and not calls
    assert sent[0]["status"] == 413


def test_allowed_chunked_body_is_replayed_to_app():
    data = [
        {"type": "http.request", "body": b"123", "more_body": True},
        {"type": "http.request", "body": b"456", "more_body": False},
    ]
    received, sent, calls = run_body(data)
    assert len(received) == 2 and calls
    assert sent[0]["status"] == 200
