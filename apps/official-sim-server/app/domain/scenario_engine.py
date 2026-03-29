from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
import uuid

from app.models.models import Artifact, ArtifactType, PushEvent, PushEventStatus
from app.platforms.taobao.profile import (
    TaobaoOrderStatus,
    TaobaoRefundStatus,
    ORDER_SCENARIOS as TAOBAO_SCENARIOS,
    get_default_order_payload as taobao_order_payload,
    get_default_shipment_payload,
    get_default_refund_payload as taobao_refund_payload,
    get_default_push_payload as taobao_push_payload,
)
from app.platforms.douyin_shop.profile import (
    DouyinOrderStatus,
    DouyinRefundStatus,
    ORDER_SCENARIOS as DOUYIN_SCENARIOS,
    get_default_order_payload as douyin_order_payload,
    get_default_refund_payload as douyin_refund_payload,
    get_default_push_payload as douyin_push_payload,
)


PLATFORM_SCENARIOS = {
    "taobao": TAOBAO_SCENARIOS,
    "douyin_shop": DOUYIN_SCENARIOS,
}

PLATFORM_ORDER_PAYLOAD = {
    "taobao": taobao_order_payload,
    "douyin_shop": douyin_order_payload,
}

PLATFORM_REFUND_PAYLOAD = {
    "taobao": taobao_refund_payload,
    "douyin_shop": douyin_refund_payload,
}

PLATFORM_PUSH_PAYLOAD = {
    "taobao": taobao_push_payload,
    "douyin_shop": douyin_push_payload,
}


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
        scenarios = PLATFORM_SCENARIOS.get(platform)
        if not scenarios:
            return {"error": f"Unknown platform: {platform}"}

        scenario = scenarios.get(scenario_name)
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

        order_id = self._generate_order_id(platform, run_id)

        if platform == "taobao":
            self._handle_taobao_step(
                run_id, current_step, action_name, next_status,
                order_id, artifacts, pushes
            )
        elif platform == "douyin_shop":
            self._handle_douyin_step(
                run_id, current_step, action_name, next_status,
                order_id, artifacts, pushes
            )

        return {
            "action": action_name,
            "next_status": next_status.value if hasattr(next_status, 'value') else str(next_status),
            "order_id": order_id,
            "artifacts_created": len(artifacts),
            "pushes_created": len(pushes),
            "current_step": current_step,
        }

    def _generate_order_id(self, platform: str, run_id: UUID) -> str:
        if platform == "taobao":
            return f"TB{run_id.hex[:12].upper()}"
        elif platform == "douyin_shop":
            return f"DY{run_id.hex[:12].upper()}"
        return f"{platform.upper()}{run_id.hex[:12].upper()}"

    def _handle_taobao_step(
        self,
        run_id: UUID,
        step_no: int,
        action_name: str,
        next_status,
        order_id: str,
        artifacts: List,
        pushes: List,
    ):
        if action_name == "pay":
            order_payload = taobao_order_payload(order_id, next_status)
            artifact = self._create_order_artifact(
                run_id, step_no, "taobao", order_payload,
                "/taobao/trade/order/get", "taobao.trade.order.get"
            )
            artifacts.append(artifact)

            push_payload = taobao_push_payload("trade.OrderStatusChanged", order_id)
            push = self._create_push_event(run_id, step_no, "taobao", push_payload)
            pushes.append(push)

        elif action_name == "ship":
            from app.platforms.taobao.profile import get_default_shipment_payload
            shipment_payload = get_default_shipment_payload(order_id, "shipped")
            artifact = self._create_order_artifact(
                run_id, step_no, "taobao", shipment_payload,
                "/taobao/logistics.detail.get", "taobao.logistics.detail.get"
            )
            artifacts.append(artifact)

            push_payload = taobao_push_payload("trade.ShipSent", order_id)
            push = self._create_push_event(run_id, step_no, "taobao", push_payload)
            pushes.append(push)

        elif action_name == "confirm_receive":
            order_payload = taobao_order_payload(order_id, next_status)
            artifact = self._create_order_artifact(
                run_id, step_no, "taobao", order_payload,
                "/taobao/trade/order.get", "taobao.trade.order.get"
            )
            artifacts.append(artifact)

    def _handle_douyin_step(
        self,
        run_id: UUID,
        step_no: int,
        action_name: str,
        next_status,
        order_id: str,
        artifacts: List,
        pushes: List,
    ):
        if action_name == "pay":
            order_payload = douyin_order_payload(order_id, next_status)
            artifact = self._create_order_artifact(
                run_id, step_no, "douyin_shop", order_payload,
                "/douyin/order/get", "order.query"
            )
            artifacts.append(artifact)

            push_payload = douyin_push_payload("order.PaySuccess", order_id)
            push = self._create_push_event(run_id, step_no, "douyin_shop", push_payload)
            pushes.append(push)

        elif action_name == "ship":
            order_payload = douyin_order_payload(order_id, next_status)
            artifact = self._create_order_artifact(
                run_id, step_no, "douyin_shop", order_payload,
                "/douyin/order/get", "order.query"
            )
            artifacts.append(artifact)

            push_payload = douyin_push_payload("order.ShipSent", order_id)
            push = self._create_push_event(run_id, step_no, "douyin_shop", push_payload)
            pushes.append(push)

        elif action_name == "confirm":
            order_payload = douyin_order_payload(order_id, next_status)
            artifact = self._create_order_artifact(
                run_id, step_no, "douyin_shop", order_payload,
                "/douyin/order/get", "order.query"
            )
            artifacts.append(artifact)

            push_payload = douyin_push_payload("order.ConfirmReceived", order_id)
            push = self._create_push_event(run_id, step_no, "douyin_shop", push_payload)
            pushes.append(push)

        elif action_name == "complete":
            order_payload = douyin_order_payload(order_id, next_status)
            artifact = self._create_order_artifact(
                run_id, step_no, "douyin_shop", order_payload,
                "/douyin/order/get", "order.query"
            )
            artifacts.append(artifact)

        elif action_name == "apply_refund":
            refund_payload = douyin_refund_payload(order_id, f"REF_{order_id}", DouyinRefundStatus.APPLIED)
            artifact = self._create_order_artifact(
                run_id, step_no, "douyin_shop", refund_payload,
                "/douyin/refund/get", "refund.query"
            )
            artifacts.append(artifact)

        elif action_name == "approve_refund":
            refund_payload = douyin_refund_payload(order_id, f"REF_{order_id}", DouyinRefundStatus.REFUNDED)
            artifact = self._create_order_artifact(
                run_id, step_no, "douyin_shop", refund_payload,
                "/douyin/refund/get", "refund.query"
            )
            artifacts.append(artifact)

            push_payload = douyin_push_payload("refund.RefundSuccess", order_id)
            push = self._create_push_event(run_id, step_no, "douyin_shop", push_payload)
            pushes.append(push)

    def _create_order_artifact(
        self,
        run_id: UUID,
        step_no: int,
        platform: str,
        payload: Dict[str, Any],
        route_key: str,
        method: str,
    ) -> Artifact:
        artifact = Artifact(
            id=uuid.uuid4(),
            run_id=run_id,
            step_no=step_no,
            platform=platform,
            artifact_type=ArtifactType.API_RESPONSE,
            route_key=route_key,
            request_headers_json={"Content-Type": "application/json"},
            request_body_json={"method": method},
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

    def get_scenario_info(self, platform: str, scenario_name: str) -> Optional[Dict[str, Any]]:
        scenarios = PLATFORM_SCENARIOS.get(platform)
        if not scenarios:
            return None
        scenario = scenarios.get(scenario_name)
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
