from typing import Dict, Any, Optional
from .base import ReplyAdapter, ReplySource
from .stub import StubReplyAdapter
from .official_sim import OfficialSimReplyAdapter


class UnifiedReplyAdapter(ReplyAdapter):
    def __init__(
        self,
        use_official_sim: bool = True,
        official_sim_base_url: str = "http://localhost:8000",
        platform: str = "taobao"
    ):
        self.use_official_sim = use_official_sim
        self.platform = platform
        self.official_adapter = OfficialSimReplyAdapter(base_url=official_sim_base_url)
        self.stub_adapter = StubReplyAdapter(platform=platform)

    def get_reply(
        self,
        run_id: str,
        user_message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self.use_official_sim:
            result = self.official_adapter.get_reply(run_id, user_message, context)
            if result.get("fallback_to_stub"):
                return self.stub_adapter.get_reply(run_id, user_message, context)
            return result
        else:
            return self.stub_adapter.get_reply(run_id, user_message, context)

    def get_source(self) -> ReplySource:
        if self.use_official_sim:
            return ReplySource.OFFICIAL_SIM
        else:
            return ReplySource.STUB

    def switch_mode(self, use_official_sim: bool):
        self.use_official_sim = use_official_sim

    def get_available_modes(self) -> Dict[str, bool]:
        return {
            "use_official_sim": self.use_official_sim,
            "official_sim_available": self._check_official_sim_available(),
        }

    def _check_official_sim_available(self) -> bool:
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.official_adapter.base_url}/health")
                return response.status_code == 200
        except:
            return False
