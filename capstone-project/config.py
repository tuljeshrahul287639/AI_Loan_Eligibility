import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

MIN_CREDIT_SCORE = 620
MAX_DTI_RATIO = 0.43
MIN_INCOME = 30000
MAX_LOAN_AMOUNT = 500000

SYNTHETIC_DATA_FILE = "data/sample_applications.json"
LOG_DIR = "logs"
LOG_FILE_PATH = "logs/loan_assessment.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
POLICIES_DIR = "data"

RISK_SCORE_THRESHOLD = 70
RISK_WEIGHTS = {
    "credit": 0.35,
    "income": 0.25,
    "debt": 0.25,
    "behavioral": 0.15
}

RAG_CHUNK_SIZE = 500
RAG_OVERLAP = 100
RAG_TOP_K = 3
RAG_COLLECTION_NAME = "lending_policies"
RAG_PERSIST_DIR = "chroma_data"
CHROMADB_PATH = "chroma_data"
POLICY_DOCUMENTS_PATH = "data"

AGENT_TIMEOUT = 30
WORKFLOW_TIMEOUT = 60

REQUIRE_HUMAN_APPROVAL_ON_DISAGREEMENT = True
REQUIRE_HUMAN_APPROVAL_ON_RISKY_DECISION = True
CONFIDENCE_THRESHOLD = 0.75

USE_RAG_FOR_POLICY_RETRIEVAL = True
ENABLE_PARALLEL_AGENT_EXECUTION = True
ENABLE_AUDIT_LOGGING = True

MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2

NUM_SYNTHETIC_APPLICATIONS = 50