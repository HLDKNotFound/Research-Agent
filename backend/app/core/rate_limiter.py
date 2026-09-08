import time
from typing import Dict, List, Optional
from fastapi import HTTPException, Request, status
from app.core.cache import cache_service
from app.core.config import settings

# In-memory fallback sliding window for local testing or when Redis is offline
_in_memory_limits: Dict[str, List[float]] = {}


async def check_rate_limit(
    request: Request,
    action: str = "auth",
    max_requests: Optional[int] = None,
    window_seconds: int = 60,
) -> None:
    """
    Sliding window rate limiter guarding critical endpoints (/login, /register, /refresh)
    against credential stuffing and brute-force attacks.
    """
    limit = max_requests or settings.AUTH_RATE_LIMIT_PER_MINUTE

    # Extract client IP respecting X-Forwarded-For if behind proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and settings.BEHIND_PROXY:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    rate_key = f"v1:ratelimit:{action}:{client_ip}"
    now = time.time()

    redis_client = await cache_service.get_client()

    if redis_client:
        try:
            # Redis sliding window using sorted sets or increment
            current_count = await redis_client.incr(rate_key)
            if current_count == 1:
                await redis_client.expire(rate_key, window_seconds)

            if current_count > limit:
                ttl = await redis_client.ttl(rate_key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many {action} requests. Please try again in {max(ttl, 1)} seconds.",
                )
            return
        except HTTPException:
            raise
        except Exception:
            pass  # Fall back to in-memory sliding window

    # In-memory sliding window
    timestamps = _in_memory_limits.get(rate_key, [])
    # Filter timestamps within window
    cutoff = now - window_seconds
    timestamps = [t for t in timestamps if t > cutoff]

    if len(timestamps) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many {action} requests. Please try again later.",
        )

    timestamps.append(now)
    _in_memory_limits[rate_key] = timestamps
