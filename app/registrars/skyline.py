from app.models import AllotmentStatus, RegistrarResult
from app.registrars.base import IPORef, RegistrarAdapter


class SkylineAdapter(RegistrarAdapter):
    name = "skyline"

    async def discover(self) -> list[IPORef]:
        return []

    async def check(self, pan: str, ipo: IPORef) -> RegistrarResult:
        return RegistrarResult(
            status=AllotmentStatus.LOOKUP_FAILED,
            message="Skyline's public allotment flow is CAPTCHA-gated; no verified automated PAN endpoint is configured.",
        )
