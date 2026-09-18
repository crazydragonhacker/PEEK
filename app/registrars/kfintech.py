"""Live KFintech integration.

KFintech's current portal is a React SPA. Its IPO master list is embedded in
its content-hashed JS bundle, while the actual PAN lookup is served by the
AWS API used by the portal. We discover the issue/client id instead of
hardcoding old IPO names.
"""
import json
import re
from typing import Any

import httpx

from app.models import AllotmentStatus, RegistrarResult
from app.registrars.base import IPORef, RegistrarAdapter
from app.registrars.http import make_client, request_with_retry

SITE_URL = "https://ipostatus.kfintech.com/"
API_URL = "https://0uz601ms56.execute-api.ap-south-1.amazonaws.com/prod/api/query?type=pan"


class KFintechAdapter(RegistrarAdapter):
    name = "kfintech"

    async def discover(self) -> list[IPORef]:
        async with make_client(25) as client:
            html = (await request_with_retry(lambda: client.get(SITE_URL))).text
            match = re.search(r"(?:\./)?(static/js/main\.[A-Za-z0-9]+\.js)", html)
            if not match:
                raise RuntimeError("KFintech JS bundle could not be located")
            bundle_url = "https://ipostatus.kfintech.com/" + match.group(1)
            bundle = (await request_with_retry(lambda: client.get(bundle_url))).text

        raw = self._extract_json_array(bundle)
        refs: list[IPORef] = []
        for item in raw:
            if isinstance(item, dict) and item.get("clientId") and item.get("name"):
                refs.append(IPORef(self.name, str(item["clientId"]).strip(), str(item["name"]).strip()))
        if not refs:
            raise RuntimeError("KFintech IPO list was empty or changed format")
        return refs

    @staticmethod
    def _extract_json_array(source: str) -> list[Any]:
        marker = '"clientId"'
        idx = source.find(marker)
        while idx >= 0:
            start = source.rfind("[", 0, idx)
            if start >= 0:
                depth = 0
                quoted = False
                escaped = False
                for pos in range(start, len(source)):
                    ch = source[pos]
                    if quoted:
                        if escaped:
                            escaped = False
                        elif ch == "\\":
                            escaped = True
                        elif ch == '"':
                            quoted = False
                        continue
                    if ch == '"':
                        quoted = True
                    elif ch == "[":
                        depth += 1
                    elif ch == "]":
                        depth -= 1
                        if depth == 0:
                            candidate = source[start:pos + 1]
                            for text in (candidate, candidate.replace('\\"', '"')):
                                try:
                                    parsed = json.loads(text)
                                    if isinstance(parsed, list):
                                        return parsed
                                except json.JSONDecodeError:
                                    pass
                            break
            idx = source.find(marker, idx + 1)
        raise RuntimeError("KFintech IPO array not found in JS bundle")

    async def check(self, pan: str, ipo: IPORef) -> RegistrarResult:
        try:
            async with make_client(15) as client:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) "
                        "Gecko/20100101 Firefox/155.0"
                    ),
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "reqparam": pan,
                    "client_id": ipo.client_id,
                    "Origin": "https://ipostatus.kfintech.com",
                    "Referer": "https://ipostatus.kfintech.com/",
                }
                response = await request_with_retry(
                    lambda: client.get(API_URL, headers=headers),
                    attempts=3,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            return RegistrarResult(
                status=AllotmentStatus.LOOKUP_FAILED,
                message=(
                    f"KFintech lookup failed: HTTP {exc.response.status_code}. "
                    f"Response: {exc.response.text[:300]}"
                ),
            )
        except Exception as exc:
            return RegistrarResult(
                status=AllotmentStatus.LOOKUP_FAILED,
                message=f"KFintech lookup failed ({exc.__class__.__name__}): {exc}",
            )

        return self._parse(data)

    @staticmethod
    def _parse(data: Any) -> RegistrarResult:
        records = data.get("data") if isinstance(data, dict) else None
        if not isinstance(records, list):
            return RegistrarResult(
                status=AllotmentStatus.LOOKUP_FAILED,
                message="KFintech returned an unexpected response shape.",
            )
        if not records:
            return RegistrarResult(
                status=AllotmentStatus.NOT_APPLIED,
                message="No application was found for this PAN against this IPO.",
            )

        record = records[0]
        if not isinstance(record, dict):
            return RegistrarResult(status=AllotmentStatus.LOOKUP_FAILED, message="KFintech returned invalid record data.")

        text = " ".join(str(v) for v in record.values())
        if re.search(r"no\s*record|not\s*found|not\s*applied|no\s*data", text, re.I):
            return RegistrarResult(status=AllotmentStatus.NOT_APPLIED, message="No application was found for this PAN against this IPO.")

        allotted_raw = record.get("All_Shares")
        applied_raw = record.get("App_Shares")
        if allotted_raw is None and applied_raw is None:
            return RegistrarResult(status=AllotmentStatus.LOOKUP_FAILED, message="KFintech returned an unrecognized response format.")

        try:
            allotted = int(str(allotted_raw or 0).replace(",", ""))
        except ValueError:
            return RegistrarResult(status=AllotmentStatus.LOOKUP_FAILED, message="KFintech returned an invalid share count.")

        if allotted > 0:
            return RegistrarResult(status=AllotmentStatus.ALLOTTED, shares_allotted=allotted, message="Shares allotted.")
        return RegistrarResult(status=AllotmentStatus.NOT_ALLOTTED, shares_allotted=0, message="Applied, but no shares were allotted.")