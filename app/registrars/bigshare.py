"""Bigshare integration.

The public lookup endpoint is real, but current Bigshare lookups require a
server-generated CAPTCHA token and answer. We deliberately do not attempt to
bypass that control. The adapter therefore discovers IPOs live and returns a
clear lookup_failed result until a legitimate CAPTCHA-token workflow is
provided by the caller/service.
"""
import re
from html import unescape

from app.models import AllotmentStatus, RegistrarResult
from app.registrars.base import IPORef, RegistrarAdapter
from app.registrars.http import make_client, request_with_retry

URL = "https://ipo.bigshareonline.com/IPO_Status.html"


class BigshareAdapter(RegistrarAdapter):
    name = "bigshare"

    async def discover(self) -> list[IPORef]:
        try:
            async with make_client(20) as client:
                html = (await request_with_retry(lambda: client.get(URL))).text
        except Exception as exc:
            raise RuntimeError(f"Bigshare IPO discovery failed ({exc.__class__.__name__})") from exc

        html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
        match = re.search(r'<select[^>]*id=["\']ddlCompany["\'][^>]*>(.*?)</select>', html, re.I | re.S)
        if not match:
            raise RuntimeError("Bigshare IPO dropdown could not be found")
        refs: list[IPORef] = []
        for value, label in re.findall(r'<option[^>]*value=["\'](\d+)["\'][^>]*>(.*?)</option>', match.group(1), re.I | re.S):
            name = unescape(re.sub(r"<[^>]+>", "", label)).strip()
            if name:
                refs.append(IPORef(self.name, value, name))
        if not refs:
            raise RuntimeError("Bigshare returned an empty IPO list")
        return refs

    async def check(self, pan: str, ipo: IPORef) -> RegistrarResult:
        return RegistrarResult(
            status=AllotmentStatus.LOOKUP_FAILED,
            message=(
                "Bigshare's current live endpoint requires a server-generated CAPTCHA "
                "token and answer. Peek does not bypass CAPTCHA, so this lookup cannot "
                "be completed automatically."
            ),
        )
