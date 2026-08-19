"""Operators — persistent, scheduled autonomous agents."""

from nes.operators.loader import load_operator
from nes.operators.manager import OperatorManager
from nes.operators.types import OperatorManifest

__all__ = ["OperatorManifest", "OperatorManager", "load_operator"]
