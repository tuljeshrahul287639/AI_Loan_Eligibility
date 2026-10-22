import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth import (
    ADMIN_ROLE,
    USER_ROLE,
    bearer,
    create_session,
    get_current_user,
    hash_password,
    verify_password,
)
from db.database import get_db
from db.models import AuthSession, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.]{3,40}$")


class SignupIn(BaseModel):
    username: str = Field(..., description="3-40 letters, numbers, dots or underscores")
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)


class LoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=40)
    password: str = Field(..., min_length=1, max_length=128)


def _session_response(db: Session, user: User) -> dict:
    return {
        "token": create_session(db, user),
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
    }


def _login(db: Session, payload: LoginIn, expected_role: str, other_page: str) -> dict:
    user = db.query(User).filter_by(username=payload.username.strip()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    if user.role != expected_role:
        raise HTTPException(status_code=403, detail=f"This account must log in on the {other_page} page")
    return _session_response(db, user)


@router.post("/signup", status_code=201)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    """Create an applicant account and log it in."""
    username = payload.username.strip()
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(status_code=400, detail="Username must be 3-40 letters, numbers, dots or underscores")
    if db.query(User).filter_by(username=username).first():
        raise HTTPException(status_code=409, detail="That username is already taken")

    user = User(
        username=username,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=USER_ROLE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _session_response(db, user)


@router.post("/user/login")
def user_login(payload: LoginIn, db: Session = Depends(get_db)):
    return _login(db, payload, USER_ROLE, other_page="admin login")


@router.post("/admin/login")
def admin_login(payload: LoginIn, db: Session = Depends(get_db)):
    return _login(db, payload, ADMIN_ROLE, other_page="applicant login")


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"username": user.username, "full_name": user.full_name, "role": user.role}


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if credentials is not None:
        db.query(AuthSession).filter_by(token=credentials.credentials).delete()
        db.commit()
    return {"status": "logged out"}
