from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.models import AllotmentStatus, RegistrarResult
from app.registrars import factory
from app.registrars.base import IPORef

client = TestClient(app)


def setup_function():
    factory._CACHE = []
    factory._CACHE_AT = 0


def fake_catalog():
    return [
        IPORef("mufg_intime", "11795", "Tata Technologies"),
        IPORef("kfintech", "12345", "Example KFin IPO"),
        IPORef("bigshare", "99", "Example Bigshare IPO"),
    ]


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_invalid_pan_is_400(monkeypatch):
    monkeypatch.setattr(factory, "_refresh", AsyncMock(return_value=fake_catalog()))
    resp = client.post("/check", json={"pan": "not-a-pan", "ipo": "Tata Technologies"})
    assert resp.status_code == 400


def test_unknown_ipo_is_404(monkeypatch):
    monkeypatch.setattr(factory, "_refresh", AsyncMock(return_value=fake_catalog()))
    resp = client.post("/check", json={"pan": "ABCDE1234F", "ipo": "no-such-ipo"})
    assert resp.status_code == 404


def test_allotted(monkeypatch):
    monkeypatch.setattr(factory, "_refresh", AsyncMock(return_value=fake_catalog()))
    adapter = factory.adapter_for(fake_catalog()[0])
    monkeypatch.setattr(
        adapter,
        "check",
        AsyncMock(return_value=RegistrarResult(status=AllotmentStatus.ALLOTTED, shares_allotted=35, message="Shares allotted.")),
    )
    resp = client.post("/check", json={"pan": "ABCDE1234F", "ipo": "Tata Technologies"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "allotted"
    assert body["shares_allotted"] == 35
    assert body["pan"] == "AB******4F"


def test_not_applied(monkeypatch):
    monkeypatch.setattr(factory, "_refresh", AsyncMock(return_value=fake_catalog()))
    adapter = factory.adapter_for(fake_catalog()[0])
    monkeypatch.setattr(
        adapter,
        "check",
        AsyncMock(return_value=RegistrarResult(status=AllotmentStatus.NOT_APPLIED, message="No application found.")),
    )
    resp = client.post("/check", json={"pan": "ABCDE1234F", "ipo": "Tata Technologies"})
    assert resp.json()["status"] == "not_applied"


def test_captcha_registrar_reports_lookup_failed(monkeypatch):
    monkeypatch.setattr(factory, "_refresh", AsyncMock(return_value=fake_catalog()))
    resp = client.post("/check", json={"pan": "ABCDE1234F", "ipo": "Example Bigshare IPO"})
    assert resp.json()["status"] == "lookup_failed"
