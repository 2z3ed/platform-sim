from typing import Dict, Any, Optional, List
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UnifiedOrder:
    order_id: str
    platform: str
    status: str
    total_amount: str
    created_at: datetime


@dataclass
class UnifiedPushEvent:
    event_type: str
    platform: str
    payload: Dict[str, Any]
    created_at: datetime


@dataclass
class UnifiedConversation:
    conversation_id: str
    platform: str
    status: str
    open_id: str
    created_at: datetime


class ArtifactMapper:
    @staticmethod
    def to_unified_order(artifact: Dict[str, Any]) -> Optional[UnifiedOrder]:
        body = artifact.get("response_body_json", {})
        if not body:
            return None
        return UnifiedOrder(
            order_id=body.get("order_id", ""),
            platform=artifact.get("platform", ""),
            status=body.get("status", ""),
            total_amount=body.get("total_amount", "0.00"),
            created_at=datetime.now(),
        )

    @staticmethod
    def to_unified_push(push_event: Dict[str, Any]) -> UnifiedPushEvent:
        return UnifiedPushEvent(
            event_type=push_event.get("event_type", ""),
            platform=push_event.get("platform", ""),
            payload=push_event.get("body_json", {}),
            created_at=push_event.get("created_at", datetime.now()),
        )

    @staticmethod
    def to_unified_conversation(artifact: Dict[str, Any]) -> Optional[UnifiedConversation]:
        body = artifact.get("response_body_json", {})
        if not body:
            return None
        return UnifiedConversation(
            conversation_id=body.get("code", ""),
            platform=artifact.get("platform", ""),
            status=body.get("status", ""),
            open_id=body.get("open_id", ""),
            created_at=datetime.now(),
        )

    @staticmethod
    def extract_order_info(artifacts: List[Dict[str, Any]]) -> List[UnifiedOrder]:
        orders = []
        for artifact in artifacts:
            if artifact.get("artifact_type") == "api_response_snapshot":
                route = artifact.get("route_key", "")
                if "order" in route or "trade" in route:
                    order = ArtifactMapper.to_unified_order(artifact)
                    if order:
                        orders.append(order)
        return orders

    @staticmethod
    def extract_conversation_info(artifacts: List[Dict[str, Any]]) -> List[UnifiedConversation]:
        conversations = []
        for artifact in artifacts:
            if artifact.get("artifact_type") == "api_response_snapshot":
                route = artifact.get("route_key", "")
                if "callback" in route or "kf" in route:
                    conv = ArtifactMapper.to_unified_conversation(artifact)
                    if conv:
                        conversations.append(conv)
        return conversations


class IntegrationAdapter:
    def __init__(self):
        self.mapper = ArtifactMapper()

    def adapt_run_to_unified(
        self,
        run_id: UUID,
        platform: str,
        artifacts: List[Dict[str, Any]],
        pushes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        orders = self.mapper.extract_order_info(artifacts)
        conversations = self.mapper.extract_conversation_info(artifacts)
        push_events = [self.mapper.to_unified_push(p) for p in pushes]

        return {
            "run_id": str(run_id),
            "platform": platform,
            "orders": [
                {
                    "order_id": o.order_id,
                    "status": o.status,
                    "total_amount": o.total_amount,
                }
                for o in orders
            ],
            "conversations": [
                {
                    "conversation_id": c.conversation_id,
                    "status": c.status,
                    "open_id": c.open_id,
                }
                for c in conversations
            ],
            "push_events": [
                {
                    "event_type": p.event_type,
                    "payload": p.payload,
                }
                for p in push_events
            ],
        }
