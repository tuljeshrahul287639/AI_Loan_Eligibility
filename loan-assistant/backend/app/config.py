"""Runtime configuration and filesystem locations."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = BASE_DIR / "policies"
DATA_DIR = Path(os.getenv("LOAN_DATA_DIR", BASE_DIR / "data"))
PDF_DIR = DATA_DIR / "applications"
CUSTOMERS_FILE = DATA_DIR / "customers.json"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Optional free, local LLM narration (Ollama). With no OLLAMA_MODEL the agents use deterministic templates.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") or None
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))
LLM_ENABLED = os.getenv("LLM_ENABLED", "1") != "0"

# Number of synthetic applications created on first start when the store is empty.
SEED_COUNT = int(os.getenv("SEED_COUNT", "12"))
