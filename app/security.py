"""PAN handling: format validation and masking for anything that gets logged
or echoed back. A PAN is personally identifying financial information, so
the raw value should never end up in logs, error messages, or stack traces.
"""
import re

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def validate_pan(pan: str) -> bool:
    return bool(PAN_RE.match(pan))


def mask_pan(pan: str) -> str:
    """ABCDE1234F -> AB******4F. Keeps just enough for the caller to
    recognise their own PAN in a log line without the full value being
    reconstructable from logs alone."""
    if len(pan) != 10:
        return "*" * len(pan)
    return f"{pan[:2]}{'*' * 6}{pan[8:]}"
