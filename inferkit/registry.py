from collections.abc import AsyncGenerator
from typing import Any, Callable

_run_fn: Callable | None = None
_stream_fn: Callable | None = None

def set_run(fn: Callable):
    global _run_fn
    _run_fn = fn

def set_stream(fn: Callable):
    global _stream_fn
    _stream_fn = fn

def get_run() -> Callable | None:
    return _run_fn

def get_stream() -> Callable | None:
    return _stream_fn

def has_run() -> bool:
    return _run_fn is not None
