import os
import textwrap
from pathlib import Path

from pydantic_settings import BaseSettings

from utils.config import load_all_config_files, load_config_file, load_settings


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


def test_resolves_env_placeholders_before_config(monkeypatch, tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "app.json").write_text('{"version": "1.0.0", "tag": "${VERSION}"}')

    monkeypatch.setenv("VERSION", "2.0.0")

    merged = load_all_config_files(cfg_dir)

    assert merged["tag"] == "2.0.0"
    assert merged["version"] == "1.0.0"


def test_resolves_placeholders_from_config(tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "app.json").write_text('{"version": "1.0.0", "tag": "${version}"}')

    merged = load_all_config_files(cfg_dir)

    assert merged["tag"] == "1.0.0"


def test_resolves_nested_dot_paths_and_lists(monkeypatch, tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    cfg_dir.joinpath("app.yaml").write_text(
        textwrap.dedent(
            """
            paths:
              logs:
                dir: /var/tmp/logs
            log_file: "${paths.logs.dir}/app.log"
            hosts:
              - "${PRIMARY_HOST}"
              - "${paths.logs.dir}"
            """
        )
    )

    monkeypatch.setenv("PRIMARY_HOST", "api.internal")

    merged = load_all_config_files(cfg_dir)

    assert merged["log_file"] == "/var/tmp/logs/app.log"
    assert merged["hosts"] == ["api.internal", "/var/tmp/logs"]


def test_missing_placeholder_becomes_empty_string(tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "app.yaml").write_text("missing: '${UNKNOWN_VAR}'\n")

    merged = load_all_config_files(cfg_dir)

    assert merged["missing"] == ""
