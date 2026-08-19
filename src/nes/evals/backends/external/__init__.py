"""External-framework subprocess backends (Hermes Agent, OpenClaw)."""

from nes.evals.backends.external.hermes_agent import HermesBackend
from nes.evals.backends.external.openclaw import OpenClawBackend

__all__ = ["HermesBackend", "OpenClawBackend"]
