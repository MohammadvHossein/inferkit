from collections.abc import Callable

from .registry import set_run, set_stream


def infer(func: Callable) -> Callable:
    set_run(func)
    return func


def _stream_decorator(func: Callable) -> Callable:
    set_stream(func)
    return func


infer.stream = _stream_decorator  # type: ignore[attr-defined]
