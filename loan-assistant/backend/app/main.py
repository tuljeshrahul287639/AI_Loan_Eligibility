"""FastAPI application: REST API plus the static web UI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .llm import Narrator
from .orchestrator import AssessmentOrchestrator
from .policy_store import PolicyStore
from .schemas import AssessmentResult, GenerateRequest, LoanApplication
from .store import ApplicationStore

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

policies = PolicyStore()
narrator = Narrator()
orchestrator = AssessmentOrchestrator(policies, narrator)
store = ApplicationStore()


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.ensure_seed()
    yield


app = FastAPI(title="AI Loan Eligibility Assessment Assistant", version="1.0.0", lifespan=lifespan)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_mode": narrator.mode,
        "llm_key_configured": narrator.configured,
        "llm_error": narrator.last_error,
        "model": config.OLLAMA_MODEL if narrator.mode == "ollama" else None,
        "applications": len(store.all()),
        "policy_clauses": len(policies.clauses),
    }


@app.get("/api/applications", response_model=list[LoanApplication])
def list_applications():
    return store.all()


@app.post("/api/synthetic/generate", response_model=list[LoanApplication])
def generate(req: GenerateRequest):
    store.generate(req.count, req.replace)
    return store.all()


@app.get("/api/applications/{application_id}/pdf")
def application_pdf(application_id: str):
    if store.get(application_id) is None:
        raise HTTPException(404, "Application not found")
    return FileResponse(store.pdf_path(application_id), media_type="application/pdf", filename=f"{application_id}.pdf")


@app.post("/api/applications/{application_id}/assess", response_model=AssessmentResult)
def assess_application(application_id: str):
    """Assess a stored application by reading its PDF, exactly as for an uploaded one."""
    if store.get(application_id) is None:
        raise HTTPException(404, "Application not found")
    try:
        return orchestrator.assess_pdf(store.pdf_path(application_id).read_bytes())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/assess/upload", response_model=AssessmentResult)
async def assess_upload(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 5 MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(422, "The uploaded file is not a PDF")
    try:
        return orchestrator.assess_pdf(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/policies")
def list_policies():
    return policies.documents()


app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
