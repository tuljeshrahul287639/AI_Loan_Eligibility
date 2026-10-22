import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.auth import can_see_application, get_current_user, require_applicant
from api.serializers import document_out
from db.database import PROJECT_DIR, get_db
from db.models import Document, User
from services.document_extractor import (
    DOCUMENT_TYPES,
    SUPPORTED_CONTENT_TYPES,
    ExtractionError,
    extract_income_fields,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = PROJECT_DIR / "uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
EXTENSION_TO_CONTENT_TYPE = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
    ".csv": "text/csv",
}


@router.get("/types")
def list_document_types():
    return DOCUMENT_TYPES


@router.post("/extract", status_code=201)
def extract_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    applicant: User = Depends(require_applicant),
    db: Session = Depends(get_db),
):
    """Store an income document and extract its fields with Gemini.

    Extraction failures are saved on the document (extraction_status=FAILED) rather than
    returned as an error, so the user can still fill in the form by hand.
    """
    if doc_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail=f"doc_type must be one of {DOCUMENT_TYPES}")

    original_name = Path(file.filename or "document").name
    extension = Path(original_name).suffix.lower()
    content_type = EXTENSION_TO_CONTENT_TYPE.get(extension)
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Supported files: PDF, PNG, JPG, TXT, CSV")

    file_bytes = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 10 MB")
    if not file_bytes:
        raise HTTPException(status_code=400, detail="File is empty")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    stored_path.write_bytes(file_bytes)

    document = Document(
        owner_id=applicant.id,
        doc_type=doc_type,
        original_filename=original_name,
        stored_path=str(stored_path),
        content_type=content_type,
        size_bytes=len(file_bytes),
        extraction_status="EXTRACTED",
    )
    try:
        document.extracted_data = extract_income_fields(file_bytes, content_type, doc_type)
    except ExtractionError as exc:
        document.extraction_status = "FAILED"
        document.extraction_error = str(exc)

    db.add(document)
    db.commit()
    db.refresh(document)
    return document_out(document)


@router.get("/{document_id}")
def get_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if document is None or not can_see_application(user, document):
        raise HTTPException(status_code=404, detail="Document not found")
    return document_out(document)
