from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class ReplySource(str, Enum):
    OFFICIAL_SIM = "official-sim"
    STUB = "stub"
    UNIFIED = "unified"


class ReplyAdapter(ABC):
    @abstractmethod
    def get_reply(
        self,
        run_id: str,
        user_message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_source(self) -> ReplySource:
        pass
