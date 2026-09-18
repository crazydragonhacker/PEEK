# Peek

Peek is a small FastAPI service that answers one question: given a PAN and an IPO, what is the allotment status?

It has no UI, accounts, history, notifications, or dashboard.

## Current status

The registrar layer has been changed from a hardcoded/mock design to live registrar discovery and lookup for the registrars whose current public endpoints could be verified:

- **KFintech** — live IPO discovery from the current SPA bundle and live PAN lookup through the portal's AWS API.
- **MUFG Intime (formerly Link Intime)** — live IPO discovery and PAN lookup through the current public AJAX endpoints.
- **Bigshare** — live IPO discovery is implemented. Its current PAN endpoint requires a server-generated CAPTCHA token, so Peek deliberately returns `lookup_failed` rather than bypassing CAPTCHA.
- **Maashitla / Skyline** — retained as explicit adapters that report `lookup_failed` until a stable, permitted automated endpoint is verified.

A registrar outage, rate limit, changed response schema, or CAPTCHA wall is always `lookup_failed`; it is never silently converted to `not_applied` or `not_allotted`.

## API

### `POST /check`

Request:

```json
{
  "pan": "ABCDE1234F",
  "ipo": "LCC Projects"
}
```

The `ipo` value may be the current registrar's displayed IPO name or its registrar-specific client id. Peek discovers current issue lists rather than relying on a permanently hardcoded IPO map.

Successful allotment example:

```json
{
  "pan": "ABC***234F",
  "ipo": "LCC Projects",
  "registrar": "kfintech",
  "status": "allotted",
  "shares_allotted": 20,
  "message": "Shares allotted.",
  "checked_at": "2026-09-15T16:00:00+00:00"
}
```

The possible normalized statuses are:

- `allotted` — application found and shares allotted.
- `not_allotted` — application found but zero shares allotted.
- `not_applied` — registrar returned a positive no-application signal.
- `lookup_failed` — Peek could not establish a reliable answer.

## Run

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then call `POST http://127.0.0.1:8000/check`.

## Tests

```bash
pytest -q
```

Tests for registrar parsing use captured response shapes so they do not require a real investor PAN.

## Important limitation

Real allotment data is personal financial information. Do not log raw PANs, do not store lookup history, and do not put PANs in URLs. The service masks PANs in its own response/logging layer.

Bigshare, Maashitla and Skyline currently expose CAPTCHA-protected public flows. Peek does not attempt to defeat those controls. A future implementation should use an explicitly permitted CAPTCHA-token workflow or an official API, rather than silently misreporting the result.
