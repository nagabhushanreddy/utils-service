import os
from pathlib import Path

from pydantic_settings import BaseSettings

from utils_api.config import load_config_file, load_settings


class _TestSettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000

    class Config:
        env_prefix = "TEST_"


def test_load_config_file_prefers_yaml(tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "settings.yaml").write_text("host: 0.0.0.0\nport: 9001\n")

    data = load_config_file(cfg_dir)
    assert data["host"] == "0.0.0.0"
    assert data["port"] == 9001


def test_load_settings_merges_env_overrides(tmp_path: Path, monkeypatch):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "settings.yaml").write_text("host: 0.0.0.0\nport: 9001\n")

    monkeypatch.setenv("TEST_PORT", "9010")

    settings = load_settings(_TestSettings, config_dir=cfg_dir)

    assert settings.host == "0.0.0.0"
    assert settings.port == 9010


def test_load_settings_accepts_json(tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "settings.json").write_text('{"host": "1.2.3.4", "port": 9100}')

    settings = load_settings(_TestSettings, config_dir=cfg_dir)

    assert settings.host == "1.2.3.4"
    assert settings.port == 9100
