"""
Async utilities — safe wrappers for CPU-bound and blocking I/O operations.

All synchronous blocking calls (spaCy, SentenceTransformer, ChromaDB,
Ollama, Tesseract OCR) must be wrapped with run_in_executor() to avoid
blocking the FastAPI event loop under concurrent request load.
"""
import asyncio
from functools import partial
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


async def run_sync(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run a synchronous (blocking) function in a thread pool executor.
    Prevents blocking the asyncio event loop.

    Usage:
        result = await run_sync(blocking_function, arg1, arg2, key=val)
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        fn = partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, fn)
    return await loop.run_in_executor(None, func, *args)


async def run_sync_with_executor(
    executor: Any, func: Callable[..., T], *args: Any, **kwargs: Any
) -> T:
    """
    Run a synchronous function in a specific executor (e.g., ProcessPoolExecutor
    for CPU-bound work that benefits from true parallelism beyond the GIL).
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        fn = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, fn)
    return await loop.run_in_executor(executor, func, *args)
