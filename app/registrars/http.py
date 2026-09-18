"""Small shared HTTP helpers for registrar adapters."""
import asyncio
import random
import httpx


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
)


def make_client(timeout: float = 20.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )


async def request_with_retry(fn, attempts: int = 3, base_delay: float = 0.6):
    last = None
    for attempt in range(attempts):
        try:
            return await fn()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last = exc
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(base_delay * (2 ** attempt) + random.random() * 0.25)
    raise last
