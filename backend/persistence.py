import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from backend.config import settings


class Base(DeclarativeBase):
    pass


class InvestigationRecord(Base):
    __tablename__ = "investigations_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    question: Mapped[str] = mapped_column(String(1000), nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ToolTraceRecord(Base):
    __tablename__ = "tool_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_db_id: Mapped[int] = mapped_column(
        ForeignKey("investigations_v2.id"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    tool: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trace_json: Mapped[str] = mapped_column(Text, nullable=False)


class EvaluationRecord(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SessionRecord(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    latest_investigation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


engine = create_engine(settings.database_url, future=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


def save_investigation(question: str, result: dict) -> int:
    init_db()
    with Session(engine) as session:
        row = InvestigationRecord(
            investigation_id=str(result.get("investigation_id", "unknown")),
            question=question,
            result_json=json.dumps(result, default=str),
        )
        session.add(row)
        session.flush()

        for sequence, item in enumerate(result.get("tool_history", []), start=1):
            session.add(
                ToolTraceRecord(
                    investigation_db_id=row.id,
                    sequence=sequence,
                    tool=str(item.get("tool", "unknown")),
                    status=str(item.get("status", "unknown")),
                    duration_ms=int(round(float(item.get("duration_ms", 0.0)))),
                    trace_json=json.dumps(item, default=str),
                )
            )

        session.commit()
        session.refresh(row)
        return row.id


def save_session(session_id: str, result: dict) -> None:
    init_db()
    payload = json.dumps(result, default=str)
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        row = session.scalar(select(SessionRecord).where(SessionRecord.session_id == session_id))
        if row is None:
            row = SessionRecord(
                session_id=session_id,
                latest_investigation_id=str(result.get("investigation_id", "unknown")),
                state_json=payload,
                updated_at=now,
            )
            session.add(row)
        else:
            row.latest_investigation_id = str(result.get("investigation_id", "unknown"))
            row.state_json = payload
            row.updated_at = now
        session.commit()


def load_session(session_id: str) -> dict | None:
    init_db()
    with Session(engine) as session:
        row = session.scalar(select(SessionRecord).where(SessionRecord.session_id == session_id))
        if row is None:
            return None
        return {
            "session_id": row.session_id,
            "latest_investigation_id": row.latest_investigation_id,
            "state": json.loads(row.state_json),
            "updated_at": row.updated_at.isoformat(),
        }


def save_evaluation_report(report: dict, evaluation_type: str = "offline") -> int:
    init_db()
    with Session(engine) as session:
        row = EvaluationRecord(
            evaluation_type=evaluation_type,
            report_json=json.dumps(report, default=str),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def recent_evaluations(limit: int = 20) -> list[dict]:
    init_db()
    with Session(engine) as session:
        rows = session.scalars(
            select(EvaluationRecord).order_by(EvaluationRecord.id.desc()).limit(limit)
        ).all()

    return [
        {
            "id": row.id,
            "evaluation_type": row.evaluation_type,
            "report": json.loads(row.report_json),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def recent_investigations(limit: int = 20) -> list[dict]:
    init_db()
    with Session(engine) as session:
        rows = session.scalars(
            select(InvestigationRecord).order_by(InvestigationRecord.id.desc()).limit(limit)
        ).all()

    return [
        {
            "id": row.id,
            "investigation_id": row.investigation_id,
            "question": row.question,
            "result": json.loads(row.result_json),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
