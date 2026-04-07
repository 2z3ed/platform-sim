import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.models import PushEvent, PushEventStatus


class PushDispatcher:
    def __init__(self, db: Session):
        self.db = db

    def create_push(
        self,
        run_id: uuid.UUID,
        step_no: int,
        platform: str,
        event_type: str,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> PushEvent:
        push_event = PushEvent(
            id=uuid.uuid4(),
            run_id=run_id,
            step_no=step_no,
            platform=platform,
            event_type=event_type,
            status=PushEventStatus.CREATED,
            headers_json=headers or {},
            body_json=body or {},
            retry_count=0,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(push_event)
        self.db.commit()
        self.db.refresh(push_event)
        return push_event

    def attempt_delivery(self, push_id: uuid.UUID, target_url: str) -> PushEvent:
        """Attempt to deliver push payload to target URL via HTTP POST."""
        import httpx
        push = self.db.query(PushEvent).filter(PushEvent.id == push_id).first()
        if not push:
            raise ValueError(f"Push event {push_id} not found")

        push.retry_count += 1
        push.sent_at = datetime.now(timezone.utc)

        try:
            resp = httpx.post(
                target_url,
                json=push.body_json,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if 200 <= resp.status_code < 300:
                push.status = PushEventStatus.SENT
            else:
                push.status = PushEventStatus.FAILED
                push.body_json["delivery_error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            push.status = PushEventStatus.FAILED
            push.body_json["delivery_error"] = str(e)[:200]

        self.db.commit()
        self.db.refresh(push)
        return push

    def mark_sent(self, push_id: uuid.UUID) -> Optional[PushEvent]:
        push = self.db.query(PushEvent).filter(PushEvent.id == push_id).first()
        if push:
            push.status = PushEventStatus.SENT
            push.sent_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(push)
        return push

    def mark_acked(self, push_id: uuid.UUID) -> Optional[PushEvent]:
        push = self.db.query(PushEvent).filter(PushEvent.id == push_id).first()
        if push:
            push.status = PushEventStatus.ACKED
            push.acked_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(push)
        return push

    def mark_failed(self, push_id: uuid.UUID) -> Optional[PushEvent]:
        push = self.db.query(PushEvent).filter(PushEvent.id == push_id).first()
        if push:
            push.status = PushEventStatus.FAILED
            push.retry_count += 1
            self.db.commit()
            self.db.refresh(push)
        return push

    def get_by_id(self, push_id: uuid.UUID) -> Optional[PushEvent]:
        return self.db.query(PushEvent).filter(PushEvent.id == push_id).first()

    def list_by_run(self, run_id: uuid.UUID) -> List[PushEvent]:
        return (
            self.db.query(PushEvent)
            .filter(PushEvent.run_id == run_id)
            .order_by(PushEvent.step_no.desc(), PushEvent.created_at.desc())
            .all()
        )

    def list_by_run_and_step(self, run_id: uuid.UUID, step_no: int) -> List[PushEvent]:
        return (
            self.db.query(PushEvent)
            .filter(PushEvent.run_id == run_id, PushEvent.step_no == step_no)
            .order_by(PushEvent.created_at.desc())
            .all()
        )

    def replay(self, push_id: uuid.UUID) -> PushEvent:
        push = self.get_by_id(push_id)
        if not push:
            raise ValueError(f"Push event {push_id} not found")

        new_push = PushEvent(
            id=uuid.uuid4(),
            run_id=push.run_id,
            step_no=push.step_no,
            platform=push.platform,
            event_type=push.event_type,
            status=PushEventStatus.REPLAYED,
            headers_json=push.headers_json,
            body_json=push.body_json,
            retry_count=0,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(new_push)
        self.db.commit()
        self.db.refresh(new_push)
        return new_push
