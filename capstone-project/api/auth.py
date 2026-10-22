"""Accounts, password hashing and login sessions."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import config
from db.database import get_db
from db.models import AuthSession, User

USER_ROLE = "USER"
ADMIN_ROLE = "ADMIN"
SESSION_DAYS = 7
PBKDF2_ITERATIONS = 200_000

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, expected = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(digest, expected)


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token=token,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    return token


def ensure_admin_account(db: Session) -> None:
    """Create or update the admin account from ADMIN_USERNAME / ADMIN_PASSWORD in .env."""
    if not config.ADMIN_USERNAME or not config.ADMIN_PASSWORD:
        return
    admin = db.query(User).filter_by(username=config.ADMIN_USERNAME).first()
    if admin is None:
        db.add(
            User(
                username=config.ADMIN_USERNAME,
                full_name="Administrator",
                password_hash=hash_password(config.ADMIN_PASSWORD),
                role=ADMIN_ROLE,
            )
        )
    else:
        admin.role = ADMIN_ROLE
        admin.password_hash = hash_password(config.ADMIN_PASSWORD)
    db.commit()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Please log in first")
    session = db.get(AuthSession, credentials.credentials)
    now = datetime.now(timezone.utc)
    if session is None or session.expires_at.replace(tzinfo=session.expires_at.tzinfo or timezone.utc) < now:
        raise HTTPException(status_code=401, detail="Your session has ended. Please log in again")
    return session.user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != ADMIN_ROLE:
        raise HTTPException(status_code=403, detail="This page is for the admin only")
    return user


def require_applicant(user: User = Depends(get_current_user)) -> User:
    if user.role != USER_ROLE:
        raise HTTPException(status_code=403, detail="Applicant accounts only")
    return user


def can_see_application(user: User, application) -> bool:
    """Admins see everything. Applicants see only the applications they submitted."""
    return user.role == ADMIN_ROLE or application.owner_id == user.id
