import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import ensure_admin_account
from api.routes import applications, auth, documents
from db.database import SessionLocal, init_db
from orchestrator import LoanProcessingOrchestrator
from utils.logging_setup import setup_logging

# rag/rag_pipeline.py prints emoji; redirected Windows stdout defaults to cp1252 and crashes on them
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    with SessionLocal() as db:
        ensure_admin_account(db)
    app.state.orchestrator = LoanProcessingOrchestrator()
    yield


app = FastAPI(title="AI Loan Eligibility API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(applications.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
