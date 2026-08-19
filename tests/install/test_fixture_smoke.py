"""Smoke test that the tmp_nes_home fixture works."""

from __future__ import annotations

from pathlib import Path

from nes.core import config as config_mod


def test_fixture_redirects_default_config_dir(tmp_nes_home: Path) -> None:
    assert config_mod.DEFAULT_CONFIG_DIR == tmp_nes_home
    assert tmp_nes_home.exists()
    assert (tmp_nes_home / ".state").exists()
    assert (tmp_nes_home / ".state" / "models").exists()


def test_fixture_redirects_config_path(tmp_nes_home: Path) -> None:
    assert config_mod.DEFAULT_CONFIG_PATH == tmp_nes_home / "config.toml"
