from fastapi import Request


def get_request_id(request: Request) -> str | None:
    """Expose the correlation id to route handlers without leaking framework state."""

    return getattr(request.state, "request_id", None)
