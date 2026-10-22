import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.auth import can_see_application, get_current_user, require_admin, require_applicant, ADMIN_ROLE
from api.schemas import ApplicationSubmit, LoanApplicationIn
from api.serializers import application_detail, application_summary
from data.synthetic_data_generator import load_curated_applications
from db.database import get_db
from db.models import Application, Document, Review, User

router = APIRouter(prefix="/api/applications", tags=["applications"])

STATUS_BY_DECISION = {
    "APPROVE": "APPROVED",
    "REJECT": "REJECTED",
    "REVIEW": "PENDING_REVIEW",
    "ESCALATE": "PENDING_REVIEW",
}
STATUSES = {"APPROVED", "REJECTED", "PENDING_REVIEW"}


def new_applicant_id() -> str:
    return f"APP-{uuid.uuid4().hex[:8].upper()}"


def _visible_applications(db: Session, user: User):
    """Admins query every application; applicants query only their own."""
    query = db.query(Application)
    if user.role != ADMIN_ROLE:
        query = query.filter(Application.owner_id == user.id)
    return query


def _document_step(documents: list[Document]) -> dict:
    """First step of the assessment: what the uploaded documents contributed."""
    if not documents:
        return {
            "title": "Read the uploaded documents",
            "agent": "Document reader",
            "status": "INFO",
            "explanation": "No documents were uploaded, so the figures come from the form only.",
            "inputs": {},
            "outputs": {},
        }
    failed = [doc for doc in documents if doc.extraction_status != "EXTRACTED"]
    fields_read = sum(
        1 for doc in documents if doc.extracted_data for value in doc.extracted_data.values() if value is not None
    )
    return {
        "title": "Read the uploaded documents",
        "agent": "Document reader",
        "status": "REVIEW" if failed else "PASS",
        "explanation": (
            f"{len(documents)} document(s) read with Gemini."
            + (f" {len(failed)} could not be read and must be checked by hand." if failed else "")
        ),
        "inputs": {f"{doc.doc_type}": doc.original_filename for doc in documents},
        "outputs": {"Income fields found": str(fields_read)},
    }


def _assess_and_save(
    request: Request,
    db: Session,
    data: dict,
    documents: list[Document],
    owner: User | None,
) -> Application:
    result = request.app.state.orchestrator.process_application(data)
    trace = [_document_step(documents)] + (result.get("workflow_trace") or [])
    for number, step in enumerate(trace, start=1):
        step["number"] = number

    application = Application(
        workflow_trace=trace,
        owner_id=owner.id if owner else None,
        applicant_id=data["applicant_id"],
        applicant_name=data["name"],
        status=STATUS_BY_DECISION.get(result.get("decision"), "PENDING_REVIEW"),
        decision=result.get("decision") or "REVIEW",
        confidence_score=float(result.get("confidence_score") or 0.0),
        requires_human_approval=bool(result.get("requires_human_approval")),
        reason=result.get("reason"),
        workflow_duration_seconds=float(result.get("workflow_duration_seconds") or 0.0),
        input_data=data,
        financial_analysis=result.get("financial_analysis"),
        risk_analysis=result.get("risk_analysis"),
        recommendation_analysis=result.get("recommendation_analysis"),
    )
    application.documents = documents
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def _load_unlinked_documents(db: Session, document_ids: list[int], owner: User) -> list[Document]:
    documents = db.query(Document).filter(Document.id.in_(document_ids)).all() if document_ids else []
    found_ids = {doc.id for doc in documents}
    missing = [doc_id for doc_id in document_ids if doc_id not in found_ids]
    linked = [doc.id for doc in documents if doc.application_id is not None]
    not_yours = [doc.id for doc in documents if doc.owner_id != owner.id]
    if missing or linked or not_yours:
        raise HTTPException(
            status_code=400,
            detail=f"Documents not found or already used: {sorted(set(missing + linked + not_yours))}",
        )
    return documents


@router.get("/samples")
def list_sample_applications(
    limit: int = Query(10, ge=1, le=50),
    _admin: User = Depends(require_admin),
):
    return load_curated_applications()[:limit]


@router.post("/assess")
def assess_application(
    application: LoanApplicationIn,
    request: Request,
    _user: User = Depends(get_current_user),
):
    """Run the agents without saving anything."""
    data = application.model_dump()
    data["applicant_id"] = data["applicant_id"] or new_applicant_id()
    return request.app.state.orchestrator.process_application(data)


@router.post("/import-samples")
def import_sample_applications(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Assess the bundled sample applications and save them, skipping ones already saved.

    Samples have no owner, so only the admin sees them.
    """
    imported, skipped = 0, 0
    for sample in load_curated_applications()[:limit]:
        if db.query(Application).filter_by(applicant_id=sample["applicant_id"]).first():
            skipped += 1
            continue
        data = {key: value for key, value in sample.items() if key != "expected_outcome"}
        _assess_and_save(request, db, data, documents=[], owner=None)
        imported += 1
    return {"imported": imported, "skipped": skipped}


@router.post("", status_code=201)
def create_application(
    payload: ApplicationSubmit,
    request: Request,
    applicant: User = Depends(require_applicant),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude={"document_ids"})
    data["applicant_id"] = data["applicant_id"] or new_applicant_id()
    if db.query(Application).filter_by(applicant_id=data["applicant_id"]).first():
        raise HTTPException(status_code=409, detail=f"Applicant ID {data['applicant_id']} already exists")

    documents = _load_unlinked_documents(db, payload.document_ids, applicant)
    application = _assess_and_save(request, db, data, documents, owner=applicant)
    return application_detail(application)


@router.get("/stats")
def application_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admins see totals for all applications; applicants see counts for their own."""
    rows = (
        _visible_applications(db, user)
        .with_entities(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )
    counts = {status: 0 for status in STATUSES}
    counts.update({status: count for status, count in rows})
    return {"total": sum(counts.values()), **counts}


@router.get("")
def list_applications(
    status: str | None = Query(None, description="APPROVED, REJECTED or PENDING_REVIEW"),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if status is not None and status not in STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(STATUSES)}")
    query = _visible_applications(db, user)
    if status:
        query = query.filter(Application.status == status)
    applications = query.order_by(Application.created_at.desc(), Application.id.desc()).limit(limit).all()
    return [application_summary(app) for app in applications]


@router.get("/{application_id}")
def get_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = db.get(Application, application_id)
    if application is None or not can_see_application(user, application):
        raise HTTPException(status_code=404, detail="Application not found")
    return application_detail(application)


class ReviewIn(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    note: str = Field(..., min_length=3, max_length=500, description="Why the reviewer made this decision")


@router.post("/{application_id}/review", status_code=201)
def review_application(
    application_id: int,
    payload: ReviewIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve or reject an application that is waiting for manual review."""
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status != "PENDING_REVIEW":
        raise HTTPException(
            status_code=409,
            detail=f"Only pending applications can be reviewed (status is {application.status})",
        )

    db.add(
        Review(
            application_id=application.id,
            decision=payload.decision,
            note=payload.note.strip(),
            reviewer=admin.username,
        )
    )
    application.status = payload.decision
    db.commit()
    db.refresh(application)
    return application_detail(application)
