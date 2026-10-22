import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = PROJECT_DIR / "data" / "loan_applications.db"

# Read DATABASE_URL from the project's .env even if this module is imported before config.py
load_dotenv(dotenv_path=PROJECT_DIR / ".env", override=True)

# Which database to use, in order:
#   1. LOAN_DB_PATH   - a SQLite file (the tests use this so they never touch the real data)
#   2. DATABASE_URL   - e.g. mysql+pymysql://user:password@localhost:3306/loan_eligibility
#   3. otherwise      - the SQLite file in data/
LOAN_DB_PATH = os.getenv("LOAN_DB_PATH")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if LOAN_DB_PATH:
    DB_PATH = Path(LOAN_DB_PATH)
    DATABASE_URL_IN_USE = f"sqlite:///{DB_PATH}"
elif DATABASE_URL:
    DB_PATH = None
    DATABASE_URL_IN_USE = DATABASE_URL
else:
    DB_PATH = DEFAULT_SQLITE_PATH
    DATABASE_URL_IN_USE = f"sqlite:///{DB_PATH}"

IS_SQLITE = DATABASE_URL_IN_USE.startswith("sqlite")

engine = create_engine(
    DATABASE_URL_IN_USE,
    # SQLite needs this because FastAPI uses the connection from more than one thread.
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    # MySQL closes idle connections; this reconnects instead of failing the request.
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db():
    if DB_PATH is not None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    from db import models  # noqa: F401  (registers the tables on Base)

    Base.metadata.create_all(bind=engine)
    _add_owner_columns()


# Columns added after the first version. create_all does not add columns to tables that already exist,
# so older databases get them here.
ADDED_COLUMNS = {
    "applications": {"owner_id": "INTEGER", "workflow_trace": "JSON"},
    "documents": {"owner_id": "INTEGER"},
}


def _add_owner_columns():
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, columns_to_add in ADDED_COLUMNS.items():
            existing = {column["name"] for column in inspector.get_columns(table)}
            for column, column_type in columns_to_add.items():
                if column not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
