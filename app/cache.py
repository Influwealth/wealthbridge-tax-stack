"""
Cache layer with Redis backend and transparent in-process dict fallback.

The fallback ensures the app runs without Redis in CI/test environments.
In production, set REDIS_URL to a real Redis instance.

Usage:
    from app.cache import cache_get, cache_set, cache_delete, cached

    # Decorator — caches the return value of any function
    @cached("my_prefix", ttl=300)
    def expensive_fn(arg): ...

    # Manual
    cache_set("key", value, ttl=60)
    value = cache_get("key")
"""
import json
import os
import functools
import hashlib
from typing import Any, Optional, Callable

from tax_capsule.utils.logger import get_logger

logger = get_logger("Cache")

REDIS_URL = os.getenv("REDIS_URL", "")
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "300"))  # 5 min

# --- backend selection ---
_redis_client = None
_local_cache: dict[str, Any] = {}   # fallback: in-process dict (no TTL enforcement in tests)


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not REDIS_URL:
        return None
    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        _redis_client.ping()
        logger.info(f"Redis connected: {REDIS_URL}")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}) — using in-process fallback cache")
        return None


def cache_set(key: str, value: Any, ttl: int = CACHE_DEFAULT_TTL) -> None:
    serialized = json.dumps(value, default=str)
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, serialized)
            return
        except Exception as e:
            logger.warning(f"Redis set failed ({e}), falling back to local cache")
    _local_cache[key] = serialized


def cache_get(key: str) -> Optional[Any]:
    r = _get_redis()
    if r:
        try:
            val = r.get(key)
            return json.loads(val) if val is not None else None
        except Exception as e:
            logger.warning(f"Redis get failed ({e}), trying local cache")
    val = _local_cache.get(key)
    return json.loads(val) if val is not None else None


def cache_delete(key: str) -> None:
    r = _get_redis()
    if r:
        try:
            r.delete(key)
        except Exception:
            pass
    _local_cache.pop(key, None)


def cache_clear_prefix(prefix: str) -> int:
    """Delete all keys starting with prefix. Returns count deleted."""
    count = 0
    r = _get_redis()
    if r:
        try:
            keys = r.keys(f"{prefix}*")
            if keys:
                count = r.delete(*keys)
            return count
        except Exception:
            pass
    keys_to_del = [k for k in _local_cache if k.startswith(prefix)]
    for k in keys_to_del:
        del _local_cache[k]
    return len(keys_to_del)


def _make_cache_key(prefix: str, args, kwargs) -> str:
    raw = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"


def cached(prefix: str, ttl: int = CACHE_DEFAULT_TTL):
    """
    Decorator factory. Caches the function's return value by (prefix, args, kwargs).
    The decorated function must return a JSON-serializable value.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = _make_cache_key(prefix, args, kwargs)
            hit = cache_get(key)
            if hit is not None:
                logger.info(f"Cache HIT: {key}")
                return hit
            result = fn(*args, **kwargs)
            cache_set(key, result, ttl=ttl)
            logger.info(f"Cache MISS (stored): {key}")
            return result
        return wrapper
    return decorator


def is_redis_available() -> bool:
    r = _get_redis()
    if not r:
        return False
    try:
        r.ping()
        return True
    except Exception:
        return False
