"""
Push delivery layer for official-sim-server.

Manages push delivery records for events.
When a state advance produces an event, a push delivery record is created
and an attempt is made to deliver it to configured webhook URLs.

event = fact
push = delivery attempt
"""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import threading
import uuid
import httpx

ResourceKey = Tuple[str, str, str]  # (platform, resource_type, resource_id)


class PushDelivery:
    def __init__(
        self,
        event_id: str,
        platform: str,
        resource_type: str,
        resource_id: str,
        target_url: str,
        payload: Dict[str, Any],
    ):
        self.push_id = str(uuid.uuid4())
        self.event_id = event_id
        self.platform = platform
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.target_url = target_url
        self.payload = payload
        self.delivery_status = "pending"
        self.attempt_count = 0
        self.last_error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "push_id": self.push_id,
            "event_id": self.event_id,
            "platform": self.platform,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "target_url": self.target_url,
            "delivery_status": self.delivery_status,
            "attempt_count": self.attempt_count,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PushDeliveryManager:
    def __init__(self):
        self._deliveries: Dict[str, PushDelivery] = {}
        self._by_resource: Dict[ResourceKey, List[str]] = {}
        self._lock = threading.Lock()

    def create(
        self,
        event_id: str,
        platform: str,
        resource_type: str,
        resource_id: str,
        target_url: str,
        payload: Dict[str, Any],
    ) -> PushDelivery:
        delivery = PushDelivery(event_id, platform, resource_type, resource_id, target_url, payload)
        key = (platform, resource_type, resource_id)
        with self._lock:
            self._deliveries[delivery.push_id] = delivery
            self._by_resource.setdefault(key, []).append(delivery.push_id)
        return delivery

    def get(self, push_id: str) -> Optional[PushDelivery]:
        return self._deliveries.get(push_id)

    def list_by_resource(
        self, platform: str, resource_type: str, resource_id: str
    ) -> List[PushDelivery]:
        key = (platform, resource_type, resource_id)
        with self._lock:
            ids = self._by_resource.get(key, [])
            return [self._deliveries[pid] for pid in ids if pid in self._deliveries]

    def list_all(self) -> List[PushDelivery]:
        with self._lock:
            return list(self._deliveries.values())

    def attempt_delivery(self, push_id: str) -> PushDelivery:
        delivery = self._deliveries.get(push_id)
        if not delivery:
            raise ValueError(f"Push delivery {push_id} not found")

        delivery.attempt_count += 1
        delivery.updated_at = datetime.now(timezone.utc).isoformat()

        try:
            resp = httpx.post(
                delivery.target_url,
                json=delivery.payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if 200 <= resp.status_code < 300:
                delivery.delivery_status = "acked"
            else:
                delivery.delivery_status = "failed"
                delivery.last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            delivery.delivery_status = "failed"
            delivery.last_error = str(e)[:200]

        return delivery

    def replay(self, push_id: str) -> PushDelivery:
        delivery = self._deliveries.get(push_id)
        if not delivery:
            raise ValueError(f"Push delivery {push_id} not found")
        return self.attempt_delivery(push_id)


push_delivery_manager = PushDeliveryManager()
