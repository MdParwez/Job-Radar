"""
Central place for Langfuse observability. Everything else in the app imports
`get_langfuse_handler()` and `langfuse_client` from here instead of touching
Langfuse directly, so:

  - If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY aren't set, the app runs
    completely normally with monitoring silently disabled (no crashes, no
    dangling network calls).
  - Every LLM call and every LangGraph node gets traced with latency, token
    usage, and cost the moment you *do* set the keys — zero other code changes.
"""
import os
from typing import Optional

from app.core.config import settings

_handler = None
_client = None


def _configured() -> bool:
    return bool(settings.langfuse_public_key and settings.langfuse_secret_key)


def init_langfuse() -> None:
    """Call once at startup. Sets env vars the Langfuse SDK reads internally,
    and eagerly constructs the shared client + callback handler."""
    global _handler, _client

    if not _configured():
        return

    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    os.environ["LANGFUSE_HOST"] = settings.langfuse_host

    from langfuse import get_client
    from langfuse.langchain import CallbackHandler

    _client = get_client()
    _handler = CallbackHandler()


def get_langfuse_handler():
    """Returns a Langfuse CallbackHandler to pass into `config={"callbacks": [...]}`
    for any LangChain/LangGraph invocation, or None if monitoring is off."""
    return _handler


def get_langfuse_client():
    """Returns the raw Langfuse client (for manual scoring, flushing, etc.),
    or None if monitoring is off."""
    return _client


def is_enabled() -> bool:
    return _handler is not None


def flush() -> None:
    """Force-send any buffered traces. Useful in short-lived scripts/tests;
    FastAPI's long-running process flushes on its own background schedule."""
    if _client is not None:
        _client.flush()
