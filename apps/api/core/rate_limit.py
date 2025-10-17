"""Rate limiting middleware."""

import time
from typing import Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from packages.shared import RedisClient


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.

    Uses Redis to track request counts per user/IP.
    """

    def __init__(self, app, redis_url: str):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI app
            redis_url: Redis connection URL
        """
        super().__init__(app)
        self.redis = RedisClient(redis_url)

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.

        Args:
            request: HTTP request
            call_next: Next middleware

        Returns:
            HTTP response
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/healthz", "/readyz"]:
            return await call_next(request)

        # Get user identifier (API key, user ID, or IP)
        identifier = self._get_identifier(request)

        # Get rate limit for user
        limit = await self._get_rate_limit(identifier)

        # Check if rate limited
        is_allowed, remaining, reset_time = await self._check_rate_limit(
            identifier,
            limit,
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(int(reset_time - time.time())),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_identifier(self, request: Request) -> str:
        """
        Get user identifier for rate limiting.

        Priority: API key > User ID > IP address

        Args:
            request: HTTP request

        Returns:
            Identifier string
        """
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key[:10]}"  # Use prefix to avoid storing full key

        # Try to get user from JWT (would need to decode)
        # For now, use IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def _get_rate_limit(self, identifier: str) -> int:
        """
        Get rate limit for identifier.

        Args:
            identifier: User identifier

        Returns:
            Requests per day limit
        """
        # TODO: Look up user's plan and return appropriate limit
        # For now, use default
        if identifier.startswith("api_key:"):
            return 10000  # Pro tier default
        else:
            return 100  # Free tier / IP-based

    async def _check_rate_limit(
        self,
        identifier: str,
        limit: int,
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            identifier: User identifier
            limit: Requests per day limit

        Returns:
            Tuple of (is_allowed, remaining, reset_timestamp)
        """
        # Get current day (midnight UTC)
        now = time.time()
        day_start = int(now - (now % 86400))  # 86400 = seconds in day
        reset_time = day_start + 86400

        # Redis key for this day
        key = f"rate_limit:{identifier}:{day_start}"

        # Get current count
        current_count = await self.redis.get(key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)

        # Check if over limit
        if current_count >= limit:
            return False, 0, reset_time

        # Increment counter
        new_count = current_count + 1
        ttl = reset_time - int(now)
        await self.redis.set(key, new_count, ttl=ttl)

        remaining = limit - new_count

        return True, remaining, reset_time
