"""Tests for speech configuration."""

from nes.core.config import NESConfig, SpeechConfig


def test_speech_config_defaults():
    cfg = SpeechConfig()
    assert cfg.backend == "auto"
    assert cfg.model == "base"
    assert cfg.language == ""
    assert cfg.device == "auto"
    assert cfg.compute_type == "float16"


def test_nes_config_has_speech():
    cfg = NESConfig()
    assert hasattr(cfg, "speech")
    assert isinstance(cfg.speech, SpeechConfig)
    assert cfg.speech.backend == "auto"


def test_nes_system_has_speech_backend():
    """NESSystem has a speech_backend attribute."""
    from nes.system import NESSystem

    assert "speech_backend" in NESSystem.__dataclass_fields__
