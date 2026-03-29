from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
import uuid

from app.models.models import Artifact, ArtifactType, PushEvent, PushEventStatus
from app.platforms.taobao.profile import (
    TaobaoOrderStatus,
    TaobaoRefundStatus,
    ORDER_SCENARIOS,
    validate_status_transition,
    get_default_order_payload,
    get_default_shipment_payload,
    get_default_refund_payload,
    get_default_push_payload,
)


class ScenarioEngine:
    def __init__(self, db: Session):
        self.db = db

    def execute_step(
        self,
        run_id: UUID,
        platform: str,
        scenario_name: str,
        current_step: int,
        action: Optional[str] = None,
    ) -> Dict[str, Any]:
        if platform != "taobao":
            return {"error": f"Unknown platform: {platform}"}

        scenario = ORDER_SCENARIOS.get(scenario_name)
        if not scenario:
            return {"error": f"Unknown scenario: {scenario_name}"}

        steps = scenario.get("steps", [])
        if current_step >= len(steps):
            return {"error": "No more steps in scenario", "current_step": current_step}

        step_config = steps[current_step]
        action_name = step_config.get("action")
        next_status = step_config.get("next_status")

        if action and action != action_name:
            return {"error": f"Expected action '{action_name}', got '{action}'"}

        artifacts = []
        pushes = []

        order_id = f"TB{run_id.hex[:12].upper()}"
        if action_name == "pay":
            order_payload = get_default_order_payload(order_id, next_status)
            artifact = self._create_order_artifact(run_id, current_step, order_payload)
            artifacts.append(artifact)

            push_payload = get_default_push_payload("trade.OrderStatusChanged", order_id)
            push = self._create_push_event(run_id, current_step, platform, push_payload)
            pushes.append(push)

        elif action_name == "ship":
            shipment_payload = get_default_shipment_payload(order_id, "shipped")
            artifact = self._create_shipment_artifact(run_id, current_step, shipment_payload)
            artifacts.append(artifact)

            push_payload = get_default_push_payload("trade.ShipSent", order_id)
            push = self._create_push_event(run_id, current_step, platform, push_payload)
            pushes.append(push)

        elif action_name == "confirm_receive":
            order_payload = get_default_order_payload(order_id, next_status)
            artifact = self._create_order_artifact(run_id, current_step, order_payload)
            artifacts.append(artifact)

        return {
            "action": action_name,
            "next_status": next_status.value,
            "order_id": order_id,
            "artifacts_created": len(artifacts),
            "pushes_created": len(pushes),
            "current_step": current_step,
        }

    def _create_order_artifact(
        self,
        run_id: UUID,
        step_no: int,
        payload: Dict[str, Any],
    ) -> Artifact:
        artifact = Artifact(
            id=uuid.uuid4(),
            run_id=run_id,
            step_no=step_no,
            platform="taobao",
            artifact_type=ArtifactType.API_RESPONSE,
            route_key="/taobao/trade/order/get",
            request_headers_json={"Content-Type": "application/json"},
            request_body_json={"method": "taobao.trade.order.get"},
            response_headers_json={"Content-Type": "application/json"},
            response_body_json=payload,
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def _create_shipment_artifact(
        self,
        run_id: UUID,
        step_no: int,
        payload: Dict[str, Any],
    ) -> Artifact:
        artifact = Artifact(
            id=uuid.uuid4(),
            run_id=run_id,
            step_no=step_no,
            platform="taobao",
            artifact_type=ArtifactType.API_RESPONSE,
            route_key="/taobao/logistics.detail.get",
            request_headers_json={"Content-Type": "application/json"},
            request_body_json={"method": "taobao.logistics.detail.get"},
            response_headers_json={"Content-Type": "application/json"},
            response_body_json=payload,
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def _create_push_event(
        self,
        run_id: UUID,
        step_no: int,
        platform: str,
        payload: Dict[str, Any],
    ) -> PushEvent:
        from datetime import datetime, timezone
        push = PushEvent(
            id=uuid.uuid4(),
            run_id=run_id,
            step_no=step_no,
            platform=platform,
            event_type=payload.get("event_type", "unknown"),
            status=PushEventStatus.CREATED,
            headers_json={"Content-Type": "application/json"},
            body_json=payload,
            retry_count=0,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(push)
        self.db.commit()
        self.db.refresh(push)
        return push

    def get_scenario_info(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        scenario = ORDER_SCENARIOS.get(scenario_name)
        if not scenario:
            return None
        return {
            "scenario_name": scenario_name,
            "initial_status": scenario.get("initial_order_status").value,
            "total_steps": len(scenario.get("steps", [])),
            "steps": [
                {"action": s.get("action"), "next_status": s.get("next_status").value}
                for s in scenario.get("steps", [])
            ],
        }
