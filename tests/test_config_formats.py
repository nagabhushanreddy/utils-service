from pathlib import Path

from utils.config import Config, load_all_config_files


def test_loads_various_formats(tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    (cfg_dir / "a.yaml").write_text("logging:\n  level: INFO\n")
    (cfg_dir / "b.json").write_text('{"database": {"host": "db"}}')
    (cfg_dir / "c.toml").write_text('[service]\nname="svc"')
    (cfg_dir / "d.ini").write_text("[section]\nkey=value\n")
    (cfg_dir / "e.conf").write_text("[other]\nflag=yes\n")

    cfg = Config()
    original_dir = cfg.config_dir
    try:
        cfg.config_dir = cfg_dir
        cfg.reload()
        assert cfg.get("logging.level") == "INFO"
        assert cfg.get("database.host") == "db"
        assert cfg.get("service.name") == "svc"
        assert cfg.get("section.key") == "value"
        assert cfg.get("other.flag") == "yes"
    finally:
        cfg.config_dir = original_dir
        cfg.reload()


def test_load_all_config_files_resolves_env(monkeypatch, tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    monkeypatch.setenv("APP_ENV", "prod")

    (cfg_dir / "app.yaml").write_text("application:\n  env: ${APP_ENV:dev}\n")

    merged = load_all_config_files(cfg_dir)
    assert merged["application"]["env"] == "prod"
