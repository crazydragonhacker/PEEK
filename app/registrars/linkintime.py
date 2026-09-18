"""Live MUFG Intime integration (formerly Link Intime)."""
import re
import xml.etree.ElementTree as ET
from typing import Any

from app.models import AllotmentStatus, RegistrarResult
from app.registrars.base import IPORef, RegistrarAdapter
from app.registrars.http import make_client, request_with_retry

BASE_URL = "https://in.mpms.mufg.com/Initial_Offer/IPO.aspx"


def parse_dataset(xml_text: str) -> list[dict[str, str]]:
    xml_text = xml_text.strip()
    if not xml_text or "<NewDataSet" not in xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError("MUFG returned invalid XML") from exc
    rows: list[dict[str, str]] = []
    for table in root.iter():
        if table.tag.split("}")[-1].lower() != "table":
            continue
        row = {child.tag.split("}")[-1]: (child.text or "").strip() for child in table}
        if row:
            rows.append(row)
    return rows


class LinkIntimeAdapter(RegistrarAdapter):
    name = "mufg_intime"

    async def discover(self) -> list[IPORef]:
        async with make_client(20) as client:
            response = await request_with_retry(lambda: client.post(f"{BASE_URL}/GetDetails", json={}))
            response.raise_for_status()
            payload = response.json()
        rows = parse_dataset(payload.get("d", "") if isinstance(payload, dict) else "")
        refs = []
        for row in rows:
            client_id = row.get("company_id", "").strip()
            name = row.get("companyname", "").strip()
            if client_id and name:
                refs.append(IPORef(self.name, client_id, name))
        if not refs:
            raise RuntimeError("MUFG Intime returned no IPOs or changed its response format")
        return refs

    async def check(self, pan: str, ipo: IPORef) -> RegistrarResult:
        body = {"clientid": ipo.client_id, "PAN": pan, "IFSC": "", "CHKVAL": "1", "token": ""}
        try:
            async with make_client(20) as client:
                response = await request_with_retry(lambda: client.post(f"{BASE_URL}/SearchOnPan", json=body))
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return RegistrarResult(status=AllotmentStatus.LOOKUP_FAILED, message=f"MUFG Intime lookup failed ({exc.__class__.__name__}).")

        try:
            rows = parse_dataset(payload.get("d", ""))
        except ValueError as exc:
            return RegistrarResult(status=AllotmentStatus.LOOKUP_FAILED, message=str(exc))
        return self._parse_result(rows)

    @staticmethod
    def _parse_result(rows: list[dict[str, str]]) -> RegistrarResult:
        if not rows:
            return RegistrarResult(status=AllotmentStatus.NOT_APPLIED, message="No application was found for this PAN against this IPO.")
        row = rows[0]
        text = " ".join(row.values())
        if re.search(r"no\s*record|not\s*found|not\s*applied|no\s*data|invalid\s*pan", text, re.I):
            return RegistrarResult(status=AllotmentStatus.NOT_APPLIED, message="No application was found for this PAN against this IPO.")
        allotted_key = next((k for k in row if re.match(r"^al+ot", k, re.I)), None)
        if allotted_key is None:
            return RegistrarResult(status=AllotmentStatus.LOOKUP_FAILED, message="MUFG Intime returned an unrecognized response format.")
        raw = re.sub(r"[^0-9-]", "", row.get(allotted_key, ""))
        try:
            allotted = int(raw or 0)
        except ValueError:
            return RegistrarResult(status=AllotmentStatus.LOOKUP_FAILED, message="MUFG Intime returned an invalid share count.")
        if allotted > 0:
            return RegistrarResult(status=AllotmentStatus.ALLOTTED, shares_allotted=allotted, message="Shares allotted.")
        return RegistrarResult(status=AllotmentStatus.NOT_ALLOTTED, shares_allotted=0, message="Applied, but no shares were allotted.")
