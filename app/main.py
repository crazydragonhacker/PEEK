"""Peek — a small API that answers exactly one question: given a PAN and an
IPO, did this PAN get shares?

There is no UI, no accounts, no history. POST /check in, one of four
statuses out (allotted / not_allotted / not_applied / lookup_failed).
"""
import datetime
import logging

from fastapi import FastAPI, HTTPException

from app.models import CheckRequest, CheckResponse
from app.registrars.factory import UnknownIPOError, adapter_for, resolve_ipo
from app.security import mask_pan, validate_pan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("peek")

app = FastAPI(
    title="Peek",
    description="IPO allotment status lookup API.",
    version="0.1.0",
)


@app.post("/check", response_model=CheckResponse)
async def check_allotment(payload: CheckRequest) -> CheckResponse:
    pan = payload.pan.strip().upper()
    ipo = payload.ipo.strip()

    if not validate_pan(pan):
        # A malformed PAN is a client error, not a failed lookup — we
        # never even got as far as asking a registrar.
        raise HTTPException(status_code=400, detail="Invalid PAN format. Expected e.g. ABCDE1234F.")

    try:
        resolved = await resolve_ipo(ipo)
    except UnknownIPOError:
        raise HTTPException(status_code=404, detail=f"IPO '{ipo}' was not found in the current registrar catalogues.")

    registrar = adapter_for(resolved)

    # Never log the raw PAN — only the masked form.
    logger.info("check requested pan=%s ipo=%s registrar=%s", mask_pan(pan), resolved.name, registrar.name)

    result = await registrar.check(pan, resolved)

    return CheckResponse(
        pan=mask_pan(pan),
        ipo=resolved.name,
        registrar=registrar.name,
        status=result.status,
        shares_allotted=result.shares_allotted,
        message=result.message,
        checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
