"""
State machine for official-sim-server.

Manages state transitions for three resource types:
- order
- shipment
- after_sale

Key: (platform, resource_type, resource_id)
Storage: in-memory dict (first version)

Initial state is derived from fixture payload, not hardcoded.
"""
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime, timezone
import threading

ResourceKey = Tuple[str, str, str]  # (platform, resource_type, resource_id)


class TransitionError(Exception):
    """Raised when a state transition is not allowed by platform rules."""
    def __init__(self, platform: str, resource_type: str, resource_id: str,
                 current_status: str, requested_status: str, allowed: List[str]):
        self.platform = platform
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.current_status = current_status
        self.requested_status = requested_status
        self.allowed = allowed
        super().__init__(
            f"Invalid transition for {platform}/{resource_type}/{resource_id}: "
            f"'{current_status}' -> '{requested_status}'. "
            f"Allowed: {allowed}"
        )


class ResourceState:
    def __init__(self, platform: str, resource_type: str, resource_id: str, current_status: str):
        self.platform = platform
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.current_status = current_status
        self.history: List[Dict[str, Any]] = []
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "current_status": self.current_status,
            "history": self.history,
            "created_at": self.created_at,
        }


class StateMachine:
    def __init__(self):
        self._states: Dict[ResourceKey, ResourceState] = {}
        self._lock = threading.Lock()

    def _make_key(self, platform: str, resource_type: str, resource_id: str) -> ResourceKey:
        return (platform, resource_type, resource_id)

    def get_state(self, platform: str, resource_type: str, resource_id: str) -> Optional[ResourceState]:
        key = self._make_key(platform, resource_type, resource_id)
        return self._states.get(key)

    def init_state(
        self,
        platform: str,
        resource_type: str,
        resource_id: str,
        current_status: str,
    ) -> ResourceState:
        """Initialize state for a resource. If already exists, returns existing."""
        key = self._make_key(platform, resource_type, resource_id)
        with self._lock:
            if key not in self._states:
                self._states[key] = ResourceState(platform, resource_type, resource_id, current_status)
            return self._states[key]

    def advance(
        self,
        platform: str,
        resource_type: str,
        resource_id: str,
        new_status: str,
        action: str = "",
        validate_fn: Optional[Callable[[str, str], bool]] = None,
        allowed_statuses: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Advance resource state with optional validation.

        Args:
            validate_fn: Optional callable(current_status, new_status) -> bool.
                         If provided and returns False, raises TransitionError.
            allowed_statuses: Optional list of allowed next statuses (for error message).

        Returns:
            Transition info dict, or None if resource not initialized.

        Raises:
            TransitionError: If validate_fn rejects the transition.
        """
        key = self._make_key(platform, resource_type, resource_id)
        with self._lock:
            state = self._states.get(key)
            if not state:
                return None

            before = state.current_status

            # Validate transition if validator is provided
            if validate_fn is not None:
                if not validate_fn(before, new_status):
                    allowed = allowed_statuses or []
                    raise TransitionError(
                        platform=platform,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        current_status=before,
                        requested_status=new_status,
                        allowed=allowed,
                    )

            state.current_status = new_status
            transition = {
                "action": action,
                "before_status": before,
                "after_status": new_status,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
            state.history.append(transition)
            return transition

    def reset(self, platform: str, resource_type: str, resource_id: str) -> bool:
        key = self._make_key(platform, resource_type, resource_id)
        with self._lock:
            if key in self._states:
                del self._states[key]
                return True
            return False

    def list_states(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            states = list(self._states.values())
            if platform:
                states = [s for s in states if s.platform == platform]
            return [s.to_dict() for s in states]


state_machine = StateMachine()
