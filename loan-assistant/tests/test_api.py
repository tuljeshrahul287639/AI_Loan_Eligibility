from fastapi.testclient import TestClient

from app.main import app
from app.pdf_tools import render_pdf
from helpers import make_app


def test_api_flow():
    with TestClient(app) as client:
        health = client.get("/api/health").json()
        assert health["status"] == "ok" and health["llm_mode"] == "template" and health["policy_clauses"] > 20

        apps = client.get("/api/applications").json()
        assert len(apps) >= 12  # seeded on first start

        app_id = apps[0]["application_id"]
        pdf = client.get(f"/api/applications/{app_id}/pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

        result = client.post(f"/api/applications/{app_id}/assess")
        assert result.status_code == 200
        body = result.json()
        assert body["recommendation"]["decision"] in {"APPROVED", "CONDITIONAL", "DECLINED"}
        assert [s["agent"] for s in body["trace"]] == [
            "PDF Parser", "Router", "Financial Analysis Agent", "Risk Agent", "Recommendation Agent"]
        assert body["llm_mode"] == "template"

        generated = client.post("/api/synthetic/generate", json={"count": 3})
        assert len(generated.json()) == len(apps) + 3

        replaced = client.post("/api/synthetic/generate", json={"count": 4, "replace": True})
        assert len(replaced.json()) == 4

        docs = client.get("/api/policies").json()
        assert {d["id"] for d in docs} == {"general_credit_policy", "personal_loan_policy", "home_loan_policy", "auto_loan_policy"}


def test_upload_and_error_paths():
    with TestClient(app) as client:
        ok = client.post("/api/assess/upload", files={"file": ("a.pdf", render_pdf(make_app()), "application/pdf")})
        assert ok.status_code == 200 and ok.json()["application"]["full_name"] == "Test Person"

        assert client.post("/api/assess/upload", files={"file": ("a.txt", b"hello", "text/plain")}).status_code == 422
        assert client.post("/api/assess/upload", files={"file": ("a.pdf", b"%PDF-1.4 broken", "application/pdf")}).status_code == 422
        assert client.get("/api/applications/NOPE/pdf").status_code == 404
        assert client.post("/api/applications/NOPE/assess").status_code == 404
        assert client.post("/api/synthetic/generate", json={"count": 0}).status_code == 422
