import inspect
from collections.abc import Callable
from typing import Any

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


async def call_run(payload: dict[str, Any], files: list[bytes] | None = None) -> Any:
    fn = get_run()
    if not fn:
        raise RuntimeError("No @infer function registered")
    sig = inspect.signature(fn)
    kwargs: dict[str, Any] = {}
    if "payload" in sig.parameters:
        kwargs["payload"] = payload
    elif len(sig.parameters) >= 1:
        first = list(sig.parameters.keys())[0]
        kwargs[first] = payload
    else:
        raise TypeError("Registered @infer function must accept at least one argument (payload)")
    if "files" in sig.parameters:
        kwargs["files"] = files
    elif files:
        raise TypeError("Function does not accept 'files' but files were uploaded. Add 'files=None' param")
    result = fn(**kwargs)
    if inspect.isawaitable(result):
        result = await result
    return result


async def call_stream(payload: dict[str, Any]):
    sfn = get_stream()
    if not sfn:
        return
    result = sfn(payload)
    if inspect.isawaitable(result):
        result = await result
    if hasattr(result, "__aiter__"):
        async for chunk in result:  # type: ignore
            yield chunk
    elif hasattr(result, "__iter__"):
        for chunk in result:  # type: ignore
            yield chunk
