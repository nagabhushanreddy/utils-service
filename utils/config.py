"""Configuration loading helpers for API services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic_settings import BaseSettings
import yaml

SettingsType = TypeVar("SettingsType", bound=BaseSettings)


def load_config_file(config_dir: str | Path, filename: str = "settings") -> Dict[str, Any]:
    """Load a YAML or JSON config file from a directory if present.

    Searches for `<filename>.yaml`, `<filename>.yml`, then `<filename>.json`.
    Returns an empty dict if no file is found.
    """
    cfg_dir = Path(config_dir)
    candidates = [
        cfg_dir / f"{filename}.yaml",
        cfg_dir / f"{filename}.yml",
        cfg_dir / f"{filename}.json",
    ]

    for path in candidates:
        if path.is_file():
            if path.suffix in {".yaml", ".yml"}:
                return yaml.safe_load(path.read_text()) or {}
            if path.suffix == ".json":
                return json.loads(path.read_text())
    return {}


def load_settings(
    settings_cls: Type[SettingsType],
    *,
    config_dir: str | Path = "config",
    filename: str = "settings",
    env_file: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> SettingsType:
    """Create a `BaseSettings` instance with config file + env overrides.

    Order of precedence (highest last):
    1) Config file defaults (only if no env var exists)
    2) Environment variables (handled by BaseSettings)
    3) Provided `overrides` mapping
    """
    import os
    
    file_values = load_config_file(config_dir=config_dir, filename=filename)

    init_kwargs: Dict[str, Any] = {}
    if env_file:
        init_kwargs["_env_file"] = env_file
    
    # Only pass file values if no env var exists for that field
    # Get env_prefix from settings class if it exists
    env_prefix = getattr(settings_cls, "model_config", {}).get("env_prefix", "") or \
                 getattr(getattr(settings_cls, "Config", None), "env_prefix", "")
    
    for key, value in file_values.items():
        env_var_name = f"{env_prefix}{key}".upper()
        # Only use file value if env var doesn't exist
        if env_var_name not in os.environ:
            init_kwargs[key] = value
    
    # Create instance which will read env vars automatically
    instance = settings_cls(**init_kwargs)
    
    # Apply explicit overrides last if provided
    if overrides:
        for key, value in overrides.items():
            setattr(instance, key, value)

    return instance
