import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, Index, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class RunStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_code = Column(String(64), unique=True, nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), nullable=True)
    platform = Column(String(32), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(SQLEnum(RunStatus), default=RunStatus.CREATED, nullable=False)
    strict_mode = Column(String(1), default="1")
    push_enabled = Column(String(1), default="1")
    seed = Column(String(128), nullable=True)
    current_step = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_simulation_runs_platform_status", "platform", "status"),
        Index("ix_simulation_runs_account_status", "account_id", "status"),
    )


class SimulationEvent(Base):
    __tablename__ = "simulation_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.id"), nullable=False)
    step_no = Column(Integer, nullable=False)
    event_type = Column(String(64), nullable=False)
    source_type = Column(String(32), nullable=True)
    payload_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_simulation_events_run_step", "run_id", "step_no"),
        Index("ix_simulation_events_run_event_type", "run_id", "event_type"),
    )


class StateSnapshot(Base):
    __tablename__ = "state_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.id"), nullable=False)
    step_no = Column(Integer, nullable=False)
    auth_state_json = Column(JSON, default=dict)
    order_state_json = Column(JSON, default=dict)
    shipment_state_json = Column(JSON, default=dict)
    after_sale_state_json = Column(JSON, default=dict)
    conversation_state_json = Column(JSON, default=dict)
    push_state_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_state_snapshots_run_step", "run_id", "step_no", unique=True),
        Index("ix_state_snapshots_run_created", "run_id", "created_at"),
    )


class PushEventStatus(str, enum.Enum):
    CREATED = "created"
    SENT = "sent"
    ACKED = "acked"
    FAILED = "failed"
    REPLAYED = "replayed"


class PushEvent(Base):
    __tablename__ = "push_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.id"), nullable=False)
    step_no = Column(Integer, nullable=False)
    platform = Column(String(32), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    status = Column(SQLEnum(PushEventStatus), default=PushEventStatus.CREATED)
    headers_json = Column(JSON, default=dict)
    body_json = Column(JSON, default=dict)
    sent_at = Column(DateTime, nullable=True)
    acked_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_push_events_run_step", "run_id", "step_no"),
        Index("ix_push_events_platform_status", "platform", "status"),
        Index("ix_push_events_event_type_status", "event_type", "status"),
    )


class ArtifactType(str, enum.Enum):
    API_RESPONSE = "api_response_snapshot"
    CALLBACK = "callback_payload"
    WEBHOOK = "webhook_payload"
    MESSAGE_SYNC = "message_sync_payload"
    ERROR_RESPONSE = "error_response_payload"


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.id"), nullable=False)
    step_no = Column(Integer, nullable=False)
    platform = Column(String(32), nullable=False, index=True)
    artifact_type = Column(SQLEnum(ArtifactType), nullable=False)
    route_key = Column(String(128), nullable=True)
    request_headers_json = Column(JSON, default=dict)
    request_body_json = Column(JSON, default=dict)
    response_headers_json = Column(JSON, default=dict)
    response_body_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_artifacts_run_step", "run_id", "step_no"),
        Index("ix_artifacts_platform_type", "platform", "artifact_type"),
        Index("ix_artifacts_route_key", "route_key"),
    )


class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("simulation_runs.id"), nullable=False)
    report_version = Column(String(32), default="1.0")
    summary_json = Column(JSON, default=dict)
    expected_json = Column(JSON, default=dict)
    actual_json = Column(JSON, default=dict)
    issues_json = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_evaluation_reports_run_version", "run_id", "report_version", unique=True),
    )
