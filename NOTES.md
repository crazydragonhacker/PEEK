# Implementation note

The original version had a clean FastAPI shape and registrar abstraction, but its Link Intime and KFintech URLs/response schemas were placeholders and three adapters were stubs. It also depended on a hardcoded IPO-to-registrar JSON file.

The registrar layer has now been overhauled around the current live portals. KFintech and MUFG Intime discover their current issue/client IDs from the same data used by their public portals. Bigshare discovers its current dropdown entries and has the real lookup endpoint documented in code, but its current endpoint requires a server-generated CAPTCHA token. The implementation intentionally does not bypass that control and therefore reports `lookup_failed` for automatic Bigshare checks.

The other important correction is status handling: an empty/unrecognized response is never assumed to mean `not_applied`. Only an explicit no-record response becomes `not_applied`; an unknown schema, network error, HTTP failure, or CAPTCHA wall becomes `lookup_failed`.

If starting again, the next step would be to obtain a legitimate integration path for the CAPTCHA-protected registrars (or official APIs) and add end-to-end tests using controlled test applications. The current tests focus on parsing and error classification because a real PAN should not be embedded in the repository.
