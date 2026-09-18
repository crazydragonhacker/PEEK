"""Dynamic IPO -> registrar resolver.

The old project used a hardcoded IPO mapping. That goes stale as soon as a
new issue appears. We now ask the registrar portals for their current issue
lists and cache them for a short period.
"""

import asyncio
import re
import time

from app.registrars.base import IPORef, RegistrarAdapter
from app.registrars.bigshare import BigshareAdapter
from app.registrars.kfintech import KFintechAdapter
from app.registrars.linkintime import LinkIntimeAdapter
from app.registrars.maashitla import MaashitlaAdapter
from app.registrars.skyline import SkylineAdapter


class UnknownIPOError(Exception):
    """Raised when an IPO cannot be found in the registrar catalogues."""


_ADAPTERS: list[RegistrarAdapter] = [
    KFintechAdapter(),
    LinkIntimeAdapter(),
    BigshareAdapter(),
    MaashitlaAdapter(),
    SkylineAdapter(),
]

_CACHE: list[IPORef] = []
_CACHE_AT = 0.0
_CACHE_TTL = 300.0
_LOCK = asyncio.Lock()


def _normalize_name(value: str) -> str:
    """Normalize an IPO name for safe comparison."""

    value = value.strip().lower()

    # Replace punctuation/separators with spaces.
    value = re.sub(r"[-_/]+", " ", value)

    # Remove common IPO suffixes added by registrar catalogues.
    value = re.sub(r"\b(sme\s+ipo|ipo|issue)\b", " ", value)

    # Collapse multiple spaces.
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _matches(ref: IPORef, query: str) -> bool:
    """Return True when the user query safely identifies the IPO."""

    q = query.strip().lower()

    # Exact client ID match.
    if q == ref.client_id.lower():
        return True

    # Exact registrar:client_id match.
    if q == f"{ref.registrar}:{ref.client_id}".lower():
        return True

    # Exact original IPO name match.
    if q == ref.name.lower():
        return True

    # Flexible name match after normalization.
    return _normalize_name(q) == _normalize_name(ref.name)


async def _refresh() -> list[IPORef]:
    """Refresh the live IPO catalogue when the cache has expired."""

    global _CACHE, _CACHE_AT

    async with _LOCK:
        if _CACHE and time.monotonic() - _CACHE_AT < _CACHE_TTL:
            return _CACHE

        results = await asyncio.gather(
            *(adapter.discover() for adapter in _ADAPTERS),
            return_exceptions=True,
        )

        refs: list[IPORef] = []

        for result in results:
            if isinstance(result, list):
                refs.extend(result)

        if refs:
            _CACHE = refs
            _CACHE_AT = time.monotonic()

        return _CACHE


async def resolve_ipo(ipo: str) -> IPORef:
    """Resolve a user-supplied IPO name or ID to a registrar IPO reference."""

    refs = await _refresh()

    for ref in refs:
        if _matches(ref, ipo):
            return ref

    raise UnknownIPOError(ipo)


def adapter_for(ref: IPORef) -> RegistrarAdapter:
    """Return the registrar adapter responsible for the IPO."""

    for adapter in _ADAPTERS:
        if adapter.name == ref.registrar:
            return adapter

    raise UnknownIPOError(ref.name)