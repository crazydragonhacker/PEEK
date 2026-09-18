from app.models import AllotmentStatus, RegistrarResult
from app.registrars.base import IPORef, RegistrarAdapter


class MaashitlaAdapter(RegistrarAdapter):
    name = "maashitla"

    async def discover(self) -> list[IPORef]:
        # The current public portal is CAPTCHA-gated; no stable public PAN API
        # was verified. Keep the adapter explicit rather than pretending that
        # a generic POST endpoint exists.
        return []

    async def check(self, pan: str, ipo: IPORef) -> RegistrarResult:
        return RegistrarResult(
            status=AllotmentStatus.LOOKUP_FAILED,
            message="Maashitla's public allotment flow requires CAPTCHA; no verified automated PAN endpoint is configured.",
        )
