"""Bundle dataclasses that group cohesive subsystems of NESSystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nes.agents._stubs import BaseAgent
    from nes.agents.executor import AgentExecutor
    from nes.agents.manager import AgentManager
    from nes.agents.scheduler import AgentScheduler
    from nes.scheduler.scheduler import TaskScheduler
    from nes.scheduler.store import SchedulerStore
    from nes.security.audit import AuditLogger
    from nes.security.boundary import BoundaryGuard
    from nes.security.capabilities import CapabilityPolicy
    from nes.telemetry.gpu_monitor import GpuMonitor
    from nes.telemetry.store import TelemetryStore
    from nes.traces.collector import TraceCollector
    from nes.traces.store import TraceStore


@dataclass
class SecurityContext:
    """Security policy, audit, and boundary enforcement."""

    capability_policy: Optional[CapabilityPolicy] = None
    audit_logger: Optional[AuditLogger] = None
    boundary_guard: Optional[BoundaryGuard] = None


@dataclass
class Observability:
    """Telemetry, traces, and hardware monitoring."""

    telemetry_store: Optional[TelemetryStore] = None
    trace_store: Optional[TraceStore] = None
    trace_collector: Optional[TraceCollector] = None
    gpu_monitor: Optional[GpuMonitor] = None


@dataclass
class AgentRuntime:
    """Active agent and agent lifecycle managers."""

    agent: Optional[BaseAgent] = None
    agent_name: str = ""
    manager: Optional[AgentManager] = None
    scheduler: Optional[AgentScheduler] = None
    executor: Optional[AgentExecutor] = None


@dataclass
class Scheduling:
    """Task scheduler and its persistent store."""

    store: Optional[SchedulerStore] = None
    runner: Optional[TaskScheduler] = None
