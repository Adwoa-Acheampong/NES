"""Structural protocols for substituting fakes in place of NESSystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Protocol

if TYPE_CHECKING:
    from nes.core.config import NESConfig
    from nes.core.events import EventBus
    from nes.engine._stubs import InferenceEngine
    from nes.security.capabilities import CapabilityPolicy
    from nes.sessions.session import SessionStore
    from nes.tools._stubs import BaseTool
    from nes.tools.storage._stubs import MemoryBackend
    from nes.traces.collector import TraceCollector
    from nes.traces.store import TraceStore


class OrchestratorDeps(Protocol):
    """Minimum surface of NESSystem that QueryOrchestrator depends on.

    Tests can satisfy this with a lightweight class — no need to construct
    the full NESSystem dataclass or materialize every subsystem.
    """

    config: NESConfig
    bus: EventBus
    engine: InferenceEngine
    engine_key: str
    model: str
    agent_name: str
    tools: List[BaseTool]
    memory_backend: Optional[MemoryBackend]
    capability_policy: Optional[CapabilityPolicy]
    session_store: Optional[SessionStore]
    trace_store: Optional[TraceStore]
    trace_collector: Optional[TraceCollector]  # written by _run_agent

    # Optional attribute (getattr with default) — declared for type clarity.
    _skill_few_shot_examples: Any
