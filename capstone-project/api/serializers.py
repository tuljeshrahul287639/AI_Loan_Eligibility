from db.models import Application, Document, Review


def _iso(value):
    return value.isoformat() if value else None


def review_out(review: Review) -> dict:
    return {
        "id": review.id,
        "decision": review.decision,
        "note": review.note,
        "reviewer": review.reviewer,
        "created_at": _iso(review.created_at),
    }


def document_out(doc: Document) -> dict:
    return {
        "id": doc.id,
        "application_id": doc.application_id,
        "doc_type": doc.doc_type,
        "original_filename": doc.original_filename,
        "content_type": doc.content_type,
        "size_bytes": doc.size_bytes,
        "extraction_status": doc.extraction_status,
        "extraction_error": doc.extraction_error,
        "extracted_data": doc.extracted_data,
        "uploaded_at": _iso(doc.uploaded_at),
    }


def application_summary(app: Application) -> dict:
    return {
        "id": app.id,
        "applicant_id": app.applicant_id,
        "applicant_name": app.applicant_name,
        "status": app.status,
        "decision": app.decision,
        "confidence_score": app.confidence_score,
        "requires_human_approval": app.requires_human_approval,
        "reason": app.reason,
        "created_at": _iso(app.created_at),
    }


def application_detail(app: Application) -> dict:
    return {
        **application_summary(app),
        "workflow_duration_seconds": app.workflow_duration_seconds,
        "input_data": app.input_data,
        "financial_analysis": app.financial_analysis,
        "risk_analysis": app.risk_analysis,
        "recommendation_analysis": app.recommendation_analysis,
        "workflow_trace": app.workflow_trace or [],
        "documents": [document_out(doc) for doc in app.documents],
        "reviews": [review_out(review) for review in app.reviews],
    }
