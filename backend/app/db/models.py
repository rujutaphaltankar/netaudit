"""ORM models. The raw uploaded configuration is NEVER stored: only redacted evidence and parsed results."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="viewer")  # admin | viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Audit(Base):
    __tablename__ = "audits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    line_count: Mapped[int] = mapped_column(Integer)
    vendor: Mapped[str] = mapped_column(String(32), index=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parser_version: Mapped[str] = mapped_column(String(32))
    catalog_version: Mapped[str] = mapped_column(String(32))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str] = mapped_column(String(4))
    risk_level: Mapped[str] = mapped_column(String(16))
    coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    unknown: Mapped[int] = mapped_column(Integer, default=0)
    not_applicable: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON)
    parse_response: Mapped[dict[str, Any]] = mapped_column(JSON)  # ConfigParseResponse (redacted)

    created_by: Mapped[User | None] = relationship()
    findings: Mapped[list[Finding]] = relationship(back_populates="audit", cascade="all, delete-orphan",
                                                   passive_deletes=True, order_by="Finding.id")
    ai_mappings: Mapped[list[AIMapping]] = relationship(back_populates="audit", cascade="all, delete-orphan",
                                                        passive_deletes=True, order_by="AIMapping.id")


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), index=True)
    message: Mapped[str] = mapped_column(Text)
    observed: Mapped[str | None] = mapped_column(Text, nullable=True)
    unknown_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence: Mapped[list[Any]] = mapped_column(JSON, default=list)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    references: Mapped[list[Any]] = mapped_column(JSON, default=list)

    audit: Mapped[Audit] = relationship(back_populates="findings")


class AIMapping(Base):
    """An AI/heuristic suggestion for an unrecognized command. Advisory only until a human approves it,
    and even when approved it never changes a rule verdict or the score."""

    __tablename__ = "ai_mappings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    vendor: Mapped[str] = mapped_column(String(32))
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    command_text: Mapped[str] = mapped_column(Text)  # already redacted
    context: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pattern: Mapped[str] = mapped_column(String(128), index=True)
    meaning: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32))
    security_impact: Mapped[str] = mapped_column(String(16))   # positive | neutral | negative | unknown
    confidence: Mapped[str] = mapped_column(String(8))         # low | medium | high
    suggested_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(16))            # ai | heuristic | reused
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    audit: Mapped[Audit] = relationship(back_populates="ai_mappings")
