import json

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.llm.base import LLMProvider

REPORT = "Test: HbA1c   Result: 6.8 %   Reference range: 4.0 - 5.6 %   Flag: H"


class FakeProvider(LLMProvider):
    model = "fake"

    async def generate(self, system, user, json_mode=False):
        if "translate" in system.lower():
            return json.dumps({"term_meanings": ["अर्थ"]})
        return json.dumps({
            "doc_type": "lab report",
            "terms": [{"term": "HbA1c", "meaning": "A blood sugar test.",
                       "source_line": "Test: HbA1c"}],
        })

    async def stream(self, system, user):
        yield ""

    async def health(self):
        return {"ok": True, "model_installed": True}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "t.db"))
    monkeypatch.setattr(main, "provider", FakeProvider())
    with TestClient(main.app) as c:
        yield c


def test_full_roundtrip(client):
    r = client.post("/api/explain", data={"text": REPORT})
    assert r.status_code == 200
    body = r.json()
    doc_id = body["id"]
    assert body["result"]["findings"][0]["status"] == "above"
    assert client.get(f"/api/documents/{doc_id}").status_code == 200
    assert len(client.get("/api/documents").json()) == 1
    h = client.post(f"/api/documents/{doc_id}/hindi")
    assert h.status_code == 200
    assert h.json()["hindi"]["term_meanings"] == ["अर्थ"]
    assert client.post(f"/api/documents/{doc_id}/feedback", json={"helpful": True}).status_code == 200
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert client.get(f"/api/documents/{doc_id}").status_code == 404


def test_empty_input(client):
    assert client.post("/api/explain", data={"text": "   "}).status_code == 400


def test_too_short(client):
    assert client.post("/api/explain", data={"text": "hello"}).status_code == 422


def test_too_long(client):
    assert client.post("/api/explain", data={"text": "a " * 4000}).status_code == 413


def test_bad_file_type(client):
    r = client.post("/api/explain", files={"file": ("x.exe", b"abc")})
    assert r.status_code == 400