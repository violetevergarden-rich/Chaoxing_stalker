"""Retry transient operations with exponential backoff."""

import functools
import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def retry(max_attempts: int = 3, base_delay: int = 2):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, OSError) as error:
                    last_exception = error
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        print(f"[WARN] 第 {attempt} 次失败，{delay}s 后重试...")
                        time.sleep(delay)
            raise last_exception

        return wrapper

    return decorator
