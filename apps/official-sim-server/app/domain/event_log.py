"""
Event log for official-sim-server.

Records state transitions as events. Each event includes the full platform-specific payload
after the transition, not just before/after status snippets.
"""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import threading
import uuid

ResourceKey = Tuple[str, str, str]  # (platform, resource_type, resource_id)


class EventLog:
    def __init__(self):
        self._events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record(
        self,
        event_type: str,
        platform: str,
        resource_type: str,
        resource_id: str,
        before_status: str,
        after_status: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "platform": platform,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "before_status": before_status,
            "after_status": after_status,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        with self._lock:
            self._events.append(event)
        return event

    def list_events(
        self,
        platform: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            events = self._events
            if platform:
                events = [e for e in events if e["platform"] == platform]
            if resource_type:
                events = [e for e in events if e["resource_type"] == resource_type]
            if resource_id:
                events = [e for e in events if e["resource_id"] == resource_id]
            return list(events)

    def get_events_for_resource(
        self, platform: str, resource_type: str, resource_id: str
    ) -> List[Dict[str, Any]]:
        return self.list_events(platform, resource_type, resource_id)


event_log = EventLog()
