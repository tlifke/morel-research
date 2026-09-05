"""SQLAlchemy models — see docs/DATA_MODEL.md for the as-built reference."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    study: Mapped[str] = mapped_column(String, default="010-open-harness-model-comparison")
    condition: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    spec: Mapped[str | None] = mapped_column(String, nullable=True)
    tag: Mapped[str | None] = mapped_column(String, nullable=True)
    run_dir: Mapped[str] = mapped_column(String)
    workspace_dir: Mapped[str] = mapped_column(String)
    session_file: Mapped[str | None] = mapped_column(String, nullable=True)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    tokens_reasoning: Mapped[int] = mapped_column(Integer, default=0)
    tokens_cache_read: Mapped[int] = mapped_column(Integer, default=0)
    tokens_cache_write: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    pricing_source: Mapped[str | None] = mapped_column(String, nullable=True)
    audit_clean: Mapped[bool] = mapped_column(Boolean, default=True)
    audit_violations: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    answers: Mapped[list["Answer"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    comparisons_a = relationship("Comparison", foreign_keys="Comparison.run_a_id", back_populates="run_a")
    comparisons_b = relationship("Comparison", foreign_keys="Comparison.run_b_id", back_populates="run_b")
    feedback: Mapped[list["WrittenFeedback"]] = relationship(back_populates="run")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, unique=True)
    text: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_by: Mapped[str] = mapped_column(String)  # agent | human | both
    value_type: Mapped[str] = mapped_column(String)  # bool | int_1_5 | text
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    answers: Mapped[list["Answer"]] = relationship(back_populates="question")


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("run_id", "question_id", "judge", name="uq_answer_run_question_judge"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    judge: Mapped[str] = mapped_column(String)  # agent | human
    value: Mapped[dict | list | str | int | bool | None] = mapped_column(JSONB, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_model: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[Run] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship(back_populates="answers")


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_a_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    run_b_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    better: Mapped[str] = mapped_column(String)  # a | b | tie
    dimensions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run_a = relationship("Run", foreign_keys=[run_a_id], back_populates="comparisons_a")
    run_b = relationship("Run", foreign_keys=[run_b_id], back_populates="comparisons_b")


class WrittenFeedback(Base):
    __tablename__ = "written_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    anchor_type: Mapped[str] = mapped_column(String)  # run | file | tool_call
    anchor_ref: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[Run | None] = relationship(back_populates="feedback")
