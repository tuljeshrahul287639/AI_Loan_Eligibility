import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
# override=True so the project's .env wins over any stale GOOGLE_API_KEY already set in the OS environment
load_dotenv(dotenv_path=env_path, override=True)

GOOGLE_API_KEY = (os.getenv("GOOGLE_API_KEY") or "").strip() or None
GEMINI_MODEL = "gemini-3.5-flash"

# Admin login for approving or rejecting pending applications. Set both in .env; review is disabled without them.
ADMIN_USERNAME = (os.getenv("ADMIN_USERNAME") or "").strip() or None
ADMIN_PASSWORD = (os.getenv("ADMIN_PASSWORD") or "").strip() or None

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

# Underwriting policy. Sources: data/sample_documents/lending_policy_core.txt and
# data/lending_policies.txt. Where those two files disagree, the stricter/clearer value is noted.
MIN_CREDIT_SCORE = 620              # hard reject below this
MIN_MONTHLY_INCOME = 1500           # core policy (₹1,500/mo). lending_policies.txt says ₹30,000 - conflict
MIN_INCOME = MIN_MONTHLY_INCOME     # used by the risk and financial tools; same value as the income check
MAX_DTI_RATIO = 0.43                # approve up to 43% debt-to-income (incl. the new loan payment)
CRITICAL_DTI_RATIO = 0.50           # automatic rejection above 50%
MIN_LOAN_AMOUNT = 50000             # core policy
MAX_LOAN_AMOUNT = 500000            # core policy
MAX_LOAN_TO_ANNUAL_INCOME = 5       # loan must not exceed 5x annual income
MIN_YEARS_EMPLOYED = 1              # lending_policies.txt (core policy says 6 months) - stricter value used
MAX_RECENT_INQUIRIES = 3            # more than this sends the file to manual review
MAX_DELINQUENCIES = 1               # two or more delinquencies send the file to manual review

SYNTHETIC_DATA_FILE = "data/sample_applications.json"
CURATED_DATA_FILE = "data/curated_sample_applications.json"  # one example per outcome, see expected_outcome
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
PARALLEL_EXECUTION = True
ENABLE_AUDIT_LOGGING = True

MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2
RETRY_INITIAL_DELAY = 1
RETRY_EXPONENTIAL_BASE = 2

NUM_SYNTHETIC_APPLICATIONS = 50
