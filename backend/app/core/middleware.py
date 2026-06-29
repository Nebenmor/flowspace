import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.redis import redis_client

RATE_LIMIT = 60        # max requests
WINDOW_SECONDS = 60    # per minute


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Identify the requester — prefer user id from JWT, fall back to IP
        identifier = self._get_identifier(request)
        bucket = int(time.time() // WINDOW_SECONDS)
        key = f"rate:{identifier}:{bucket}"

        try:
            count = await redis_client.incr(key)
            if count == 1:
                # First request in this window — set expiry
                await redis_client.expire(key, WINDOW_SECONDS * 2)

            if count > RATE_LIMIT:
                retry_after = WINDOW_SECONDS - (int(time.time()) % WINDOW_SECONDS)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Too many requests.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
        except Exception:
            # If Redis is unavailable, fail open — don't block the request
            pass

        return await call_next(request)

    def _get_identifier(self, request: Request) -> str:
        """
        Try to extract user ID from Authorization header.
        Falls back to client IP for unauthenticated requests.
        """
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
            # Use first 16 chars of token as bucket key — avoids storing full JWT
            return f"user:{token[:16]}"
        return f"ip:{request.client.host}"