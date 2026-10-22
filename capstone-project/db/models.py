from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    """A login account. Applicants sign up themselves; the admin account is created from .env."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))  # USER / ADMIN
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    """A signed-in session. The token is sent by the browser as a Bearer header."""

    __tablename__ = "auth_sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class Application(Base):
    """One loan application and the outcome of the multi-agent assessment."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    applicant_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    applicant_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), index=True)  # APPROVED / REJECTED / PENDING_REVIEW
    decision: Mapped[str] = mapped_column(String(20))  # APPROVE / REJECT / REVIEW / ESCALATE
    confidence_score: Mapped[float] = mapped_column(Float)
    requires_human_approval: Mapped[bool] = mapped_column(default=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workflow_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    input_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    financial_analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    risk_analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    recommendation_analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    workflow_trace: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    documents: Mapped[list["Document"]] = relationship(back_populates="application")
    reviews: Mapped[list["Review"]] = relationship(back_populates="application", order_by="Review.created_at")


class Review(Base):
    """A human decision on an application that the agents sent to manual review."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    decision: Mapped[str] = mapped_column(String(20))  # APPROVED / REJECTED
    note: Mapped[str] = mapped_column(Text)
    reviewer: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="reviews")


class Document(Base):
    """An uploaded income document and the fields extracted from it."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    application_id: Mapped[Optional[int]] = mapped_column(ForeignKey("applications.id"), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(40))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    extraction_status: Mapped[str] = mapped_column(String(20))  # EXTRACTED / FAILED
    extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Optional[Application]] = relationship(back_populates="documents")
