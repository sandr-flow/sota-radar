"""Rate limiter for API calls."""

from aiolimiter import AsyncLimiter

# 1 request per second for Mistral free tier
# Using 0.95 RPS to stay safely under the limit
MISTRAL_RATE_LIMITER = AsyncLimiter(1, 1.05)


async def with_rate_limit(limiter: AsyncLimiter = MISTRAL_RATE_LIMITER):
    """Acquire rate limit before API call.

    Usage:
        await with_rate_limit()
        response = await api_call()
    """
    await limiter.acquire()
