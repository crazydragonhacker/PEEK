# Implementation Notes

## Technology Choices

- **Python** — chosen because it provides strong HTTP, parsing, testing, and
  asynchronous programming support and is familiar to the developer.
- **FastAPI** — chosen for its lightweight API design, automatic OpenAPI/Swagger
  documentation, request validation, and straightforward async support.
- **httpx** — used for asynchronous HTTP requests to registrar endpoints.
- **pytest** — used for automated parser and API tests.
- **Pydantic** — used for request/response validation and consistent data models.

## Starting Point

The original project had a clean FastAPI structure and registrar abstraction, but some registrar integrations were placeholders or stubs. Link Intime and KFintech used placeholder URLs/response schemas, and the project relied on a hardcoded IPO-to-registrar mapping.

## Changes Implemented

The registrar layer was redesigned around live registrar catalogues.

### KFintech

* Implemented live IPO discovery.
* Implemented live PAN-based allotment lookup.
* Uses the current API used by the public IPO-status portal.
* Added parsing for allotted, not allotted, and no-application responses.
* Verified the complete `/check` flow with a real allotment-status lookup.

### MUFG Intime

* Implemented live IPO discovery.
* Implemented live PAN lookup through the current public AJAX endpoints.
* Added parsing for the XML dataset returned by the registrar.
* Verified the complete `/check` flow with a live lookup.

### Bigshare

* Implemented live IPO discovery from the registrar's current IPO dropdown.
* The current lookup flow requires a server-generated CAPTCHA token.
* Peek deliberately does not attempt to bypass CAPTCHA.
* Automatic lookups therefore return `lookup_failed` when the CAPTCHA-protected flow cannot be completed.

### Maashitla and Skyline

Adapters are retained, but their automated lookup flows are not considered complete until a stable and permitted endpoint can be verified.

## Important Status Handling

A major implementation requirement was to distinguish between an unsuccessful lookup and a genuine "not allotted" result.

Peek uses four normalized statuses:

* `allotted` — an application was found and shares were allotted.
* `not_allotted` — an application was found but zero shares were allotted.
* `not_applied` — the registrar provided a reliable indication that no application exists for the PAN.
* `lookup_failed` — Peek could not establish a reliable result.

Therefore:

```text
Network error       -> lookup_failed
HTTP failure        -> lookup_failed
Unexpected schema   -> lookup_failed
CAPTCHA wall        -> lookup_failed

No application      -> not_applied
Application + 0     -> not_allotted
Application + shares -> allotted
```

This prevents Peek from incorrectly telling an investor that they were not allotted shares when the registrar lookup itself failed.

## Main Difficulties

The main challenge was not the FastAPI layer. The difficult part was integrating with registrar systems because each registrar uses different:

* IPO discovery mechanisms.
* Request formats.
* Response formats.
* Internal endpoints.
* Anti-automation controls.

Some registrar portals also change their frontend or API implementation over time, making permanently hardcoded endpoints unreliable.

## CAPTCHA Limitation

Bigshare's current automated lookup flow requires a server-generated CAPTCHA token.

Peek does not attempt to defeat or bypass CAPTCHA.

A future implementation should use an explicitly permitted CAPTCHA-token workflow or an official API if one becomes available.

## Testing

The automated test suite currently contains 13 tests covering:

* PAN/API behavior.
* KFintech response parsing.
* Allotted status.
* Not-allotted status.
* Not-applied status.
* Unknown response handling.
* MUFG XML parsing.
* MUFG result parsing.

The complete test suite currently passes:

```text
13 passed
```

Live registrar checks were also performed for KFintech and MUFG Intime, while Bigshare's live IPO discovery and CAPTCHA-related lookup failure were verified.

Real investor PANs are not embedded in the repository or automated tests.

## What I Would Do Differently

If developing Peek again for production use, I would first establish official or explicitly permitted integration paths for each registrar before implementing the adapters.

The next improvements would be:

1. Add more verified registrar integrations.
2. Obtain an official API or permitted CAPTCHA-assisted workflow where required.
3. Add automated end-to-end tests against controlled test applications.
4. Add monitoring for registrar endpoint and response-schema changes.
5. Add rate limiting and stronger abuse protection for a public deployment.
6. Add structured logging while ensuring PAN values and other sensitive information are never recorded.

## Final Implementation Status

The core API architecture and registrar abstraction are complete.

The following are currently verified:

* FastAPI `/check` endpoint.
* Dynamic IPO discovery.
* KFintech live lookup.
* MUFG Intime live lookup.
* Bigshare live IPO discovery.
* Normalized allotment statuses.
* Lookup-failure handling.
* PAN masking.
* Automated test suite.

Bigshare, Maashitla, and Skyline automated PAN lookup remain limited by CAPTCHA or the absence of a verified stable integration path.
