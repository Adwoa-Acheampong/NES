"""Security guardrails — scanners, engine wrapper, audit, SSRF."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Optional

from nes.core.events import EventBus

logger = logging.getLogger(__name__)


@dataclass
class SecurityContext:
    """Result of setup_security() — wrapped engine, policy, audit."""

    engine: Any
    capability_policy: Any = None
    audit_logger: Any = None


def setup_security(
    config: Any,
    engine: Any,
    bus: Optional[EventBus] = None,
) -> SecurityContext:
    """Apply security guardrails to an engine based on config.

    Returns a SecurityContext. No-ops if config.security.enabled is False.
    """
    if not config.security.enabled:
        return SecurityContext(engine=engine)

    from nes.security._stubs import BaseScanner
    from nes.security.audit import AuditLogger
    from nes.security.guardrails import GuardrailsEngine
    from nes.security.scanner import PIIScanner, SecretScanner
    from nes.security.types import RedactionMode

    # Scanners + engine wrapping
    try:
        scanners: list[BaseScanner] = []
        if config.security.secret_scanner:
            scanners.append(SecretScanner())
        if config.security.pii_scanner:
            scanners.append(PIIScanner())

        if scanners:
            mode = RedactionMode(config.security.mode)
            engine = GuardrailsEngine(
                engine,
                scanners=scanners,
                mode=mode,
                scan_input=config.security.scan_input,
                scan_output=config.security.scan_output,
                bus=bus,
            )
    except Exception as exc:
        logger.debug("Failed to set up security scanners: %s", exc)

    # Capability policy
    cap_policy = None
    if config.security.capabilities.enabled:
        try:
            from nes.security.capabilities import CapabilityPolicy

            cap_policy = CapabilityPolicy(
                policy_path=config.security.capabilities.policy_path or None,
            )
        except Exception as exc:
            logger.debug("Failed to set up capability policy: %s", exc)

    # Audit logger
    audit = None
    try:
        audit = AuditLogger(
            db_path=config.security.audit_log_path,
            bus=bus,
        )
    except Exception as exc:
        logger.debug("Failed to set up audit logger: %s", exc)

    return SecurityContext(
        engine=engine,
        capability_policy=cap_policy,
        audit_logger=audit,
    )


__all__ = [
    "AuditLogger",
    "BaseScanner",
    "DEFAULT_SENSITIVE_PATTERNS",
    "GuardrailsEngine",
    "PIIScanner",
    "RedactionMode",
    "ScanFinding",
    "ScanResult",
    "SecretScanner",
    "SecurityBlockError",
    "SecurityContext",
    "SecurityEvent",
    "SecurityEventType",
    "ThreatLevel",
    "check_ssrf",
    "filter_sensitive_paths",
    "is_private_ip",
    "is_sensitive_file",
    "setup_security",
]

_LAZY_EXPORTS = {
    "AuditLogger": ("nes.security.audit", "AuditLogger"),
    "BaseScanner": ("nes.security._stubs", "BaseScanner"),
    "DEFAULT_SENSITIVE_PATTERNS": (
        "nes.security.file_policy",
        "DEFAULT_SENSITIVE_PATTERNS",
    ),
    "GuardrailsEngine": ("nes.security.guardrails", "GuardrailsEngine"),
    "PIIScanner": ("nes.security.scanner", "PIIScanner"),
    "RedactionMode": ("nes.security.types", "RedactionMode"),
    "ScanFinding": ("nes.security.types", "ScanFinding"),
    "ScanResult": ("nes.security.types", "ScanResult"),
    "SecretScanner": ("nes.security.scanner", "SecretScanner"),
    "SecurityBlockError": (
        "nes.security.guardrails",
        "SecurityBlockError",
    ),
    "SecurityEvent": ("nes.security.types", "SecurityEvent"),
    "SecurityEventType": ("nes.security.types", "SecurityEventType"),
    "ThreatLevel": ("nes.security.types", "ThreatLevel"),
    "check_ssrf": ("nes.security.ssrf", "check_ssrf"),
    "filter_sensitive_paths": (
        "nes.security.file_policy",
        "filter_sensitive_paths",
    ),
    "is_private_ip": ("nes.security.ssrf", "is_private_ip"),
    "is_sensitive_file": ("nes.security.file_policy", "is_sensitive_file"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))
