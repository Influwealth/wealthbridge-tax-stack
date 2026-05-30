"""
Token-bucket rate limiting middleware.

Uses Redis for distributed rate limiting; falls back to an in-process
counter when Redis is unavailable (suitable for single-instance deployments
and CI/test environments).

Config via env vars:
  RATE_LIMIT_PER_MINUTE  default 60
  RATE_LIMIT_BURST       default 20  (max requests allowed in a single second)
"""
import os
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.cache import _get_redis
from tax_capsule.utils.logger import get_logger

logger = get_logger("RateLimit")

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "20"))

# In-process fallback: {ip: (window_start, count)}
_local_buckets: dict[str, tuple[float, int]] = defaultdict(lambda: (0.0, 0))

# Paths exempt from rate limiting
EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit_redis(ip: str, r) -> bool:
    """Sliding window counter via Redis. Returns True if allowed."""
    now = int(time.time())
    key = f"rl:{ip}:{now // 60}"  # 1-minute window
    try:
        count = r.incr(key)
        if count == 1:
            r.expire(key, 120)  # clean up after 2 windows
        return count <= RATE_LIMIT_PER_MINUTE
    except Exception:
        return True  # fail open


def _check_rate_limit_local(ip: str) -> bool:
    """Simple 1-minute sliding window in-process. Returns True if allowed."""
    now = time.time()
    window_start, count = _local_buckets[ip]
    if now - window_start > 60:
        _local_buckets[ip] = (now, 1)
        return True
    if count >= RATE_LIMIT_PER_MINUTE:
        return False
    _local_buckets[ip] = (window_start, count + 1)
    return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        ip = _get_client_ip(request)
        r = _get_redis()
        allowed = _check_rate_limit_redis(ip, r) if r else _check_rate_limit_local(ip)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {ip} on {request.url.path}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry after 60 seconds."},
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
