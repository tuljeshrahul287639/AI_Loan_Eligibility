import os
import tempfile
from pathlib import Path

# Use a throwaway database for the test run. Must be set before api.main is imported.
os.environ["LOAN_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test_loan_applications.db")
os.environ["ADMIN_USERNAME"] = "test_admin"
os.environ["ADMIN_PASSWORD"] = "admin-test-pass"

import uuid  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from api.routes import documents as documents_route  # noqa: E402
import config  # noqa: E402

# config.py loads .env with override=True, so the real .env admin login would replace the test values.
# Set the test admin on the config module after it has loaded.
config.ADMIN_USERNAME = "test_admin"
config.ADMIN_PASSWORD = "admin-test-pass"
from services.document_extractor import ExtractionError  # noqa: E402

# Income must clear config.MIN_MONTHLY_INCOME (30000), otherwise prescreening rejects
# the application before the agents run and no agent output is returned.
VALID_APPLICATION = {
    "name": "Test Applicant",
    "monthly_income": 35000,
    "monthly_expenses": 1500,
    "credit_score": 750,
    "loan_amount": 250000,
    "existing_debts": 300,
    "years_employed": 5,
    "employment_type": "Full-time",
    "prior_delinquencies": 0,
    "bankruptcy_history": False,
    "recent_inquiries": 0,
}

EXTRACTED = {
    "name": "Test Applicant",
    "employer_name": "Acme Corp",
    "employment_type": "Full-time",
    "years_employed": 5,
    "monthly_income": 35000,
    "monthly_expenses": None,
    "existing_debts": 300,
}


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def new_applicant_token(client):
    """Sign up a fresh applicant account and return its session token."""
    username = f"applicant_{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/auth/signup",
        json={"username": username, "full_name": "Test Applicant", "password": "applicant-pass-1"},
    )
    assert response.status_code == 201
    return response.json()["token"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A logged-in applicant."""
    monkeypatch.setattr(documents_route, "UPLOAD_DIR", tmp_path / "uploads")
    with TestClient(app) as test_client:
        test_client.headers.update(bearer(new_applicant_token(test_client)))
        yield test_client


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    """A logged-in admin."""
    monkeypatch.setattr(documents_route, "UPLOAD_DIR", tmp_path / "uploads")
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/admin/login", json={"username": "test_admin", "password": "admin-test-pass"}
        )
        test_client.headers.update(bearer(response.json()["token"]))
        yield test_client


def upload(client, content=b"Monthly salary: 8000", filename="payslip.txt", doc_type="Payslip"):
    return client.post(
        "/api/documents/extract",
        files={"file": (filename, content, "text/plain")},
        data={"doc_type": doc_type},
    )


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_samples_respects_limit(admin_client):
    response = admin_client.get("/api/applications/samples", params={"limit": 3})
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_assess_does_not_save_and_returns_agent_outputs(client):
    response = client.post("/api/applications/assess", json=VALID_APPLICATION)
    body = response.json()
    assert response.status_code == 200
    assert body["applicant_id"].startswith("APP-")
    assert body["decision"] in {"APPROVE", "REJECT", "REVIEW", "ESCALATE"}
    assert "recommendation_analysis" in body


def test_assess_rejects_invalid_credit_score(client):
    payload = {**VALID_APPLICATION, "credit_score": 900}
    response = client.post("/api/applications/assess", json=payload)
    assert response.status_code == 422


def test_upload_stores_extracted_fields(client, monkeypatch):
    monkeypatch.setattr(documents_route, "extract_income_fields", lambda *args: EXTRACTED)
    response = upload(client)
    body = response.json()
    assert response.status_code == 201
    assert body["extraction_status"] == "EXTRACTED"
    assert body["extracted_data"]["monthly_income"] == 35000
    assert body["application_id"] is None


def test_upload_records_extraction_failure_without_error_status(client, monkeypatch):
    def fail(*args):
        raise ExtractionError("Gemini request failed")

    monkeypatch.setattr(documents_route, "extract_income_fields", fail)
    response = upload(client)
    body = response.json()
    assert response.status_code == 201
    assert body["extraction_status"] == "FAILED"
    assert "Gemini request failed" in body["extraction_error"]


def test_upload_rejects_unsupported_file_type(client):
    response = client.post(
        "/api/documents/extract",
        files={"file": ("virus.exe", b"MZ", "application/octet-stream")},
        data={"doc_type": "Payslip"},
    )
    assert response.status_code == 415


def test_upload_rejects_unknown_document_type(client):
    response = upload(client, doc_type="Passport scan")
    assert response.status_code == 400


def test_create_application_links_documents_and_saves_results(client, monkeypatch):
    monkeypatch.setattr(documents_route, "extract_income_fields", lambda *args: EXTRACTED)
    document_id = upload(client).json()["id"]

    response = client.post(
        "/api/applications",
        json={**VALID_APPLICATION, "document_ids": [document_id]},
    )
    body = response.json()
    assert response.status_code == 201
    assert body["status"] in {"APPROVED", "REJECTED", "PENDING_REVIEW"}
    assert body["recommendation_analysis"] is not None
    assert [doc["id"] for doc in body["documents"]] == [document_id]

    detail = client.get(f"/api/applications/{body['id']}").json()
    assert detail["input_data"]["name"] == "Test Applicant"
    assert detail["documents"][0]["extracted_data"]["employer_name"] == "Acme Corp"


def test_document_cannot_be_used_twice(client, monkeypatch):
    monkeypatch.setattr(documents_route, "extract_income_fields", lambda *args: EXTRACTED)
    document_id = upload(client).json()["id"]
    first = client.post("/api/applications", json={**VALID_APPLICATION, "document_ids": [document_id]})
    assert first.status_code == 201

    second = client.post("/api/applications", json={**VALID_APPLICATION, "document_ids": [document_id]})
    assert second.status_code == 400


def test_duplicate_applicant_id_is_rejected(client):
    payload = {**VALID_APPLICATION, "applicant_id": "APP-DUP-0001"}
    assert client.post("/api/applications", json=payload).status_code == 201
    assert client.post("/api/applications", json=payload).status_code == 409


def test_list_filters_by_status_and_stats_count_everything(client):
    client.post("/api/applications", json=VALID_APPLICATION)

    listed = client.get("/api/applications", params={"status": "REJECTED"})
    assert listed.status_code == 200
    assert all(item["status"] == "REJECTED" for item in listed.json())

    stats = client.get("/api/applications/stats").json()
    assert stats["total"] == stats["APPROVED"] + stats["REJECTED"] + stats["PENDING_REVIEW"]
    assert stats["total"] >= 1


def test_invalid_status_filter_is_rejected(client):
    response = client.get("/api/applications", params={"status": "MAYBE"})
    assert response.status_code == 400


def test_unknown_application_returns_404(client):
    assert client.get("/api/applications/999999").status_code == 404


def test_import_samples_skips_existing_on_second_run(admin_client):
    first = admin_client.post("/api/applications/import-samples", params={"limit": 2}).json()
    second = admin_client.post("/api/applications/import-samples", params={"limit": 2}).json()
    assert first["imported"] == 2
    assert second == {"imported": 0, "skipped": 2}


# --- Accounts and access rules ---

def test_signup_then_login_on_user_page(client):
    username = f"new_{uuid.uuid4().hex[:8]}"
    signup = client.post(
        "/api/auth/signup",
        json={"username": username, "full_name": "New Person", "password": "longenough1"},
    )
    assert signup.status_code == 201
    login = client.post("/api/auth/user/login", json={"username": username, "password": "longenough1"})
    assert login.status_code == 200
    assert login.json()["role"] == "USER"


def test_wrong_password_is_rejected(client):
    response = client.post("/api/auth/user/login", json={"username": "nobody_here", "password": "wrong"})
    assert response.status_code == 401


def test_admin_account_cannot_use_user_login_page(client):
    response = client.post("/api/auth/user/login", json={"username": "test_admin", "password": "admin-test-pass"})
    assert response.status_code == 403


def test_applicant_account_cannot_use_admin_login_page(client):
    token = new_applicant_token(client)
    me = client.get("/api/auth/me", headers=bearer(token)).json()
    response = client.post("/api/auth/admin/login", json={"username": me["username"], "password": "applicant-pass-1"})
    assert response.status_code == 403


def test_requests_without_login_are_refused(client):
    client.headers.pop("Authorization")
    assert client.get("/api/applications").status_code == 401
    assert client.post("/api/applications", json=VALID_APPLICATION).status_code == 401


def test_applicant_cannot_see_another_applicants_application(client):
    other_token = new_applicant_token(client)
    created = client.post("/api/applications", json={**VALID_APPLICATION, "applicant_id": "APP-PRIVATE-1"}).json()

    assert client.get(f"/api/applications/{created['id']}").status_code == 200
    assert client.get(f"/api/applications/{created['id']}", headers=bearer(other_token)).status_code == 404
    other_list = client.get("/api/applications", headers=bearer(other_token)).json()
    assert all(item["id"] != created["id"] for item in other_list)


def test_applicant_cannot_review_or_see_samples(client):
    assert client.get("/api/applications/samples").status_code == 403
    assert client.post("/api/applications/1/review", json={"decision": "APPROVED", "note": "looks fine"}).status_code == 403


def test_admin_sees_all_applications_and_can_review_pending(admin_client, client):
    created = client.post("/api/applications", json={**VALID_APPLICATION, "applicant_id": "APP-REVIEW-1"}).json()
    assert admin_client.get(f"/api/applications/{created['id']}").status_code == 200

    # The curated samples include cases the agents send to manual review
    admin_client.post("/api/applications/import-samples", params={"limit": 10})
    pending = admin_client.get("/api/applications", params={"status": "PENDING_REVIEW"}).json()
    assert pending, "expected at least one curated sample to be pending review"
    target = pending[0]["id"]

    reviewed = admin_client.post(
        f"/api/applications/{target}/review",
        json={"decision": "APPROVED", "note": "Income checked against payslip"},
    )
    assert reviewed.status_code == 201
    assert reviewed.json()["status"] == "APPROVED"
    assert reviewed.json()["reviews"][0]["reviewer"] == "test_admin"
    assert admin_client.post(
        f"/api/applications/{target}/review",
        json={"decision": "REJECTED", "note": "second attempt"},
    ).status_code == 409


def test_created_application_keeps_step_by_step_trace(client, monkeypatch):
    monkeypatch.setattr(documents_route, "extract_income_fields", lambda *args: EXTRACTED)
    document_id = upload(client).json()["id"]

    body = client.post(
        "/api/applications",
        json={**VALID_APPLICATION, "applicant_id": "APP-TRACE-1", "document_ids": [document_id]},
    ).json()

    trace = body["workflow_trace"]
    assert trace[0]["title"] == "Read the uploaded documents"
    assert trace[0]["outputs"]["Income fields found"] != "0"
    assert trace[-1]["title"] == "Final decision"
    assert [step["number"] for step in trace] == list(range(1, len(trace) + 1))
    assert all({"title", "agent", "status", "explanation"} <= set(step) for step in trace)
    assert client.get(f"/api/applications/{body['id']}").json()["workflow_trace"] == trace


def test_rejected_application_trace_ends_with_the_reason(client):
    payload = {**VALID_APPLICATION, "applicant_id": "APP-TRACE-2", "credit_score": 500}
    body = client.post("/api/applications", json=payload).json()
    assert body["status"] == "REJECTED"
    assert any(step["status"] == "FAIL" and step["title"] == "Credit score check" for step in body["workflow_trace"])
    assert body["workflow_trace"][-1]["explanation"] == body["reason"]
