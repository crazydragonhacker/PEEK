# Peek

Peek is a lightweight FastAPI service that answers one question:

> Given a PAN and an IPO, what is the allotment status?

Peek provides an API only. It intentionally has no UI, user accounts, history, notifications, or dashboard.

## Features

* Accepts a PAN and IPO name/client ID.
* Dynamically discovers current IPOs from supported registrar portals.
* Automatically selects the appropriate registrar adapter.
* Normalizes registrar-specific responses into a common API format.
* Distinguishes between:

  * `allotted`
  * `not_allotted`
  * `not_applied`
  * `lookup_failed`
* Masks PAN values in API responses.
* Does not store lookup history or expose PANs in URLs.
* Handles registrar failures without incorrectly reporting a failed lookup as "not allotted."

## Architecture

```text
                              Client
                                |
                                | POST /check
                                v
                              FastAPI API
                                |
                                v
                              IPO Resolver
                                |
  +-------------------+-------------------+------------------+
  |                   |                   |                  |
  v                   v                   v                  v
KFintech          MUFG Intime         Bigshare        Other adapters
Adapter           Adapter             Adapter          (Maashitla/
  |                   |                   |              Skyline)
  v                   v                   v                  |
Registrar API      Registrar API       CAPTCHA wall          |
  |                   |                   |                  |
  +-------------------+-------------------+------------------+
                                |
                                v
                        Normalized result
```

## Supported Registrars

### KFintech

* Live IPO discovery is implemented.
* Live PAN lookup is implemented.
* Uses the current public API used by the KFintech IPO-status portal.
* Successfully verified with a real allotment-status lookup.

### MUFG Intime

Formerly known as Link Intime.

* Live IPO discovery is implemented.
* Live PAN lookup is implemented through the current public AJAX endpoints.
* XML response parsing is implemented.
* Live lookup flow has been verified.

### Bigshare

* Live IPO discovery is implemented.
* The current PAN lookup requires a server-generated CAPTCHA token.
* Peek does not attempt to bypass or defeat CAPTCHA.
* When the lookup cannot be completed because of this restriction, Peek returns `lookup_failed`.

### Maashitla and Skyline

Adapters are retained for future integration.

They currently return `lookup_failed` until a stable and permitted automated endpoint can be verified.

## API

### `POST /check`

Request:

```json
{
  "pan": "ABCDE1234F",
  "ipo": "LCC Projects"
}
```

The `ipo` field can contain:

* The IPO name displayed by the registrar.
* A reasonable normalized variation of the IPO name.
* The registrar-specific client ID.

Peek dynamically discovers current IPO catalogues instead of depending entirely on a permanently hardcoded IPO mapping.

### Successful allotment

```json
{
  "pan": "ABC***234F",
  "ipo": "Example IPO",
  "registrar": "kfintech",
  "status": "allotted",
  "shares_allotted": 20,
  "message": "Shares allotted.",
  "checked_at": "2026-09-15T16:00:00+00:00"
}
```

### Not allotted

```json
{
  "pan": "ABC***234F",
  "ipo": "Example IPO",
  "registrar": "kfintech",
  "status": "not_allotted",
  "shares_allotted": 0,
  "message": "Applied, but no shares were allotted.",
  "checked_at": "2026-09-15T16:00:00+00:00"
}
```

### Not applied

```json
{
  "pan": "ABC***234F",
  "ipo": "Example IPO",
  "registrar": "mufg_intime",
  "status": "not_applied",
  "shares_allotted": null,
  "message": "No application was found for this PAN against this IPO.",
  "checked_at": "2026-09-15T16:00:00+00:00"
}
```

### Lookup failed

```json
{
  "pan": "ABC***234F",
  "ipo": "Example IPO",
  "registrar": "bigshare",
  "status": "lookup_failed",
  "shares_allotted": null,
  "message": "Lookup could not be completed.",
  "checked_at": "2026-09-15T16:00:00+00:00"
}
```

## Normalized Statuses

| Status          | Meaning                                                                                                                                   |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `allotted`      | Application found and shares were allotted.                                                                                               |
| `not_allotted`  | Application found but zero shares were allotted.                                                                                          |
| `not_applied`   | Registrar provided a reliable indication that no application exists for the PAN.                                                          |
| `lookup_failed` | Peek could not establish a reliable result because of an outage, rate limit, changed response format, CAPTCHA, or another lookup problem. |

**Important:** `lookup_failed` is deliberately different from `not_applied` and `not_allotted`.

Peek must never convert an unsuccessful registrar lookup into a false "not allotted" result.

## Running the Project

### 1. Create the virtual environment

Windows:

```bash
python -m venv .venv
```

### 2. Activate the virtual environment

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Command Prompt:

```cmd
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
GET /health
```

## Testing

Run the automated test suite:

```bash
pytest -q
```

The current test suite contains **13 tests**, covering API behavior and registrar response parsing.

The registrar parser tests use representative response structures and do not require a real investor PAN.

## Security and Privacy

PAN is sensitive financial information.

Peek follows these principles:

* Do not log raw PAN values.
* Mask PAN values in API responses.
* Do not store lookup history.
* Do not place PAN values in URLs.
* Use POST requests for PAN-based lookups.
* Do not include real PANs in automated tests or source code.

When testing locally, use test data or authorized PANs and avoid sharing real PAN information in public repositories or issue trackers.

## Known Limitations

### CAPTCHA-protected registrars

Some registrar portals use CAPTCHA or other anti-automation mechanisms.

Peek does not attempt to bypass these controls.

For such cases, the API returns:

```text
lookup_failed
```

rather than guessing the allotment status.

A future production implementation could support an explicitly permitted CAPTCHA-token workflow or an official registrar API.

### Registrar changes

Registrar websites and internal APIs can change without notice.

Peek therefore treats unexpected response formats and unavailable registrar services as lookup failures instead of assuming a result.

## What Could Be Improved

For a production version, the following improvements could be considered:

* Add more verified registrar integrations.
* Add an officially supported CAPTCHA-assisted workflow where permitted.
* Add stronger rate limiting and abuse protection.
* Add structured application logging without sensitive PAN data.
* Add monitoring for registrar endpoint changes.
* Add more integration tests using sanitized/captured registrar responses.
* Add persistent IPO catalogue caching if appropriate.
* Add API authentication if the service is publicly deployed.

## Project Structure

```text
peek/
│
├── app/
│   ├── main.py
│   ├── models.py
│   │
│   └── registrars/
│       ├── __init__.py
│       ├── base.py
│       ├── bigshare.py
│       ├── factory.py
│       ├── http.py
│       ├── kfintech.py
│       ├── linkintime.py
│       ├── maashitla.py
│       └── skyline.py
│
├── tests/
│   └── test_registrars.py
│
├── NOTES.md
├── README.md
├── requirements.txt
└── .gitignore
```

## Project Goal

Peek is designed as a focused API rather than a full IPO application.

Its primary goal is to provide a consistent interface over different registrar systems while preserving the distinction between:

```text
Allotted
Not Allotted
Not Applied
Lookup Failed
```

This distinction is essential because a registrar outage, CAPTCHA, or changed endpoint must not be interpreted as evidence that an investor was not allotted shares.
