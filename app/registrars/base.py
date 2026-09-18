"""Common registrar adapter contract."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.models import RegistrarResult


@dataclass(frozen=True)
class IPORef:
    """Registrar-specific identifier discovered from the registrar site."""
    registrar: str
    client_id: str
    name: str


class RegistrarAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def discover(self) -> list[IPORef]:
        """Return IPOs currently exposed by the registrar."""
        raise NotImplementedError

    @abstractmethod
    async def check(self, pan: str, ipo: IPORef) -> RegistrarResult:
        """Perform one live lookup. Never turn an unknown response into a status."""
        raise NotImplementedError
