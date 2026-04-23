"""Cache TTL simples em memória (thread-safe).

Usado para evitar consultas repetidas de schema/colunas a cada request.
"""
from __future__ import annotations

import threading
import time
from functools import wraps
from typing import Any, Callable


def ttl_cache(seconds: int = 60) -> Callable:
    """Decorator: memoriza o retorno por `seconds`. Args devem ser hasháveis."""
    def decorator(fn: Callable) -> Callable:
        store: dict[tuple, tuple[float, Any]] = {}
        lock = threading.Lock()

        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            with lock:
                hit = store.get(key)
                if hit and hit[0] > now:
                    return hit[1]
            value = fn(*args, **kwargs)
            with lock:
                store[key] = (now + seconds, value)
            return value

        def invalidate() -> None:
            with lock:
                store.clear()

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper

    return decorator
