import os
import sys
import tempfile
from pathlib import Path

# Isolate test data and disable the LLM before the app modules are imported.
os.environ["LOAN_DATA_DIR"] = tempfile.mkdtemp(prefix="loan-assistant-tests-")
os.environ["LLM_ENABLED"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
