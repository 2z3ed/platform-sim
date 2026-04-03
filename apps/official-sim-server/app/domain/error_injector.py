"""
Error injector for official-sim-server.

Per-resource error injection. Never global.
Supports:
- once: trigger once then clear
- ttl: trigger for N requests then clear
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import threading

ResourceKey = Tuple[str, str, str]  # (platform, resource_type, resource_id)


class ErrorInjection:
    def __init__(self, error_type: int, once: bool = False, ttl: int = 1):
        self.error_type = error_type
        self.once = once
        self.ttl = ttl
        self.remaining = ttl
        self.created_at = datetime.now(timezone.utc).isoformat()

    def consume(self) -> bool:
        """Returns True if error should be injected, decrements ttl."""
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True

    def is_expired(self) -> bool:
        return self.remaining <= 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "once": self.once,
            "ttl": self.ttl,
            "remaining": self.remaining,
            "created_at": self.created_at,
        }


class ErrorInjector:
    def __init__(self):
        self._errors: Dict[ResourceKey, ErrorInjection] = {}
        self._lock = threading.Lock()

    def _make_key(self, platform: str, resource_type: str, resource_id: str) -> ResourceKey:
        return (platform, resource_type, resource_id)

    def inject(
        self,
        platform: str,
        resource_type: str,
        resource_id: str,
        error_type: int,
        once: bool = True,
        ttl: int = 1,
    ) -> ErrorInjection:
        key = self._make_key(platform, resource_type, resource_id)
        with self._lock:
            injection = ErrorInjection(error_type, once, ttl)
            self._errors[key] = injection
            return injection

    def check(self, platform: str, resource_type: str, resource_id: str) -> Optional[ErrorInjection]:
        """Check if error should be injected. Consumes one use if triggered."""
        key = self._make_key(platform, resource_type, resource_id)
        with self._lock:
            injection = self._errors.get(key)
            if injection and injection.consume():
                if injection.is_expired():
                    del self._errors[key]
                return injection
            return None

    def remove(self, platform: str, resource_type: str, resource_id: str) -> bool:
        key = self._make_key(platform, resource_type, resource_id)
        with self._lock:
            if key in self._errors:
                del self._errors[key]
                return True
            return False

    def list_errors(self, platform: Optional[str] = None) -> list:
        with self._lock:
            errors = list(self._errors.items())
            if platform:
                errors = [(k, v) for k, v in errors if k[0] == platform]
            return [
                {
                    "platform": k[0],
                    "resource_type": k[1],
                    "resource_id": k[2],
                    **v.to_dict(),
                }
                for k, v in errors
            ]


error_injector = ErrorInjector()
