"""File-backed store for synthetic customer applications and their PDFs."""
import json
import threading

from . import config
from .generator import generate_applications
from .pdf_tools import render_pdf
from .schemas import LoanApplication


class ApplicationStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        config.PDF_DIR.mkdir(parents=True, exist_ok=True)
        self._apps: dict[str, LoanApplication] = {}
        if config.CUSTOMERS_FILE.exists():
            for row in json.loads(config.CUSTOMERS_FILE.read_text(encoding="utf8")):
                app = LoanApplication(**row)
                self._apps[app.application_id] = app

    def all(self) -> list[LoanApplication]:
        return list(self._apps.values())

    def get(self, application_id: str) -> LoanApplication | None:
        return self._apps.get(application_id)

    def pdf_path(self, application_id: str):
        return config.PDF_DIR / f"{application_id}.pdf"

    def generate(self, count: int, replace: bool = False) -> list[LoanApplication]:
        with self._lock:
            if replace:
                for app in self._apps.values():
                    self.pdf_path(app.application_id).unlink(missing_ok=True)
                self._apps.clear()
            start = 1001 + max((int(a.application_id.split("-")[1]) - 1000 for a in self._apps.values()), default=0)
            created = generate_applications(count, start_index=start)
            for app in created:
                self._apps[app.application_id] = app
                self.pdf_path(app.application_id).write_bytes(render_pdf(app))
            config.CUSTOMERS_FILE.write_text(
                json.dumps([a.model_dump() for a in self._apps.values()], indent=2), encoding="utf8"
            )
            return created

    def ensure_seed(self) -> None:
        if not self._apps:
            self.generate(config.SEED_COUNT)
