from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String, create_engine, insert, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL")


class AuditPersistenceError(RuntimeError):
    pass


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    action: str
    resource: str
    decision: str
    details: dict[str, Any] = Field(default_factory=dict)


class Base(DeclarativeBase):
    pass


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource: Mapped[str] = mapped_column(String(240), nullable=False)
    decision: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class AuditLog:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._session_factory: sessionmaker | None = None
        self._database_url = DATABASE_URL
        self.ensure_persistent()

    def ensure_persistent(self) -> bool:
        if self._session_factory:
            try:
                with self._session_factory() as session:
                    session.execute(text("SELECT 1"))
                return True
            except SQLAlchemyError:
                self._session_factory = None

        if not self._database_url:
            return False

        try:
            engine = create_engine(self._database_url, pool_pre_ping=True)
            Base.metadata.create_all(engine)
            self._session_factory = sessionmaker(bind=engine)
            return True
        except SQLAlchemyError:
            self._session_factory = None
            return False

    def requires_persistence(self) -> bool:
        return bool(self._database_url)

    @property
    def is_persistent(self) -> bool:
        return self.ensure_persistent()

    def record(
        self,
        *,
        actor: str,
        action: str,
        resource: str,
        decision: str,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            actor=actor,
            action=action,
            resource=resource,
            decision=decision,
            details=details or {},
        )
        if self.ensure_persistent() and self._session_factory:
            try:
                with self._session_factory.begin() as session:
                    session.execute(insert(AuditEventRow).values(**event.model_dump()))
                return event
            except SQLAlchemyError:
                if self.requires_persistence():
                    self._session_factory = None
                    raise AuditPersistenceError("audit persistence write failed")
                self._events.append(event)
                return event

        if self.requires_persistence():
            raise AuditPersistenceError("audit persistence unavailable")

        self._events.append(event)
        return event

    def list_events(self, limit: int = 50) -> list[AuditEvent]:
        if self.ensure_persistent() and self._session_factory:
            try:
                with self._session_factory() as session:
                    rows = session.scalars(
                        select(AuditEventRow)
                        .order_by(AuditEventRow.timestamp.desc())
                        .limit(limit)
                    ).all()
                return [
                    AuditEvent(
                        id=row.id,
                        timestamp=row.timestamp,
                        actor=row.actor,
                        action=row.action,
                        resource=row.resource,
                        decision=row.decision,
                        details=row.details,
                    )
                    for row in rows
                ]
            except SQLAlchemyError:
                if self.requires_persistence():
                    raise AuditPersistenceError("audit persistence read failed")
                pass

        return list(reversed(self._events[-limit:]))


audit_log = AuditLog()
