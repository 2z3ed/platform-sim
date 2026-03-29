from typing import Dict, Any, List
from .state import OrchestratorState, AgentStatus


def create_initial_state() -> OrchestratorState:
    return OrchestratorState()


def start_node(state: OrchestratorState) -> OrchestratorState:
    state.status = AgentStatus.PROCESSING
    state.messages.append({
        "role": "system",
        "content": f"Processing order {state.current_order_id} on {state.current_platform}"
    })
    return state


def error_node(state: OrchestratorState, error: str) -> OrchestratorState:
    state.status = AgentStatus.FAILED
    state.errors.append(error)
    state.messages.append({
        "role": "system",
        "content": f"Error: {error}"
    })
    return state


def end_node(state: OrchestratorState) -> OrchestratorState:
    state.status = AgentStatus.COMPLETED
    state.messages.append({
        "role": "system",
        "content": "Orchestration completed"
    })
    state.next_node = "end"
    return state
