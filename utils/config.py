"""Configuration loading helpers for API services.

This module provides flexible configuration management with support for:
- Multiple config file formats (JSON, YAML)
- Environment variable resolution with ${VAR_NAME} syntax
- Directory auto-creation
- Singleton pattern for global config instances
- Dot notation for nested config access
- Pydantic BaseSettings integration
"""

from __future__ import annotations

import configparser
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback for older interpreters
    try:
        import tomli as tomllib  # type: ignore
    except Exception:
        tomllib = None

from pydantic_settings import BaseSettings
import yaml
from dotenv import load_dotenv

# Load .env file at module import time
load_dotenv()

SettingsType = TypeVar("SettingsType", bound=BaseSettings)

_PLACEHOLDER_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


_PLACEHOLDER_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


def _get_value_from_path(root: Any, path: str) -> Any:
    """Retrieve a value from a nested mapping/list using dot notation.

    Supports numeric list indices in the path. Returns None when a path segment
    is missing.
    """
    if root is None:
        return None

    current: Any = root
    for part in path.split('.'):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            if 0 <= idx < len(current):
                current = current[idx]
            else:
                return None
        else:
            return None

    return current


def resolve_placeholders(value: Any, root: Any | None = None, env: os._Environ[str] | Dict[str, str] = os.environ) -> Any:
    """Recursively resolve ${VAR} placeholders within a structure.

    Resolution order: environment variable (env-first) -> value from `root`
    using dot notation -> placeholder default (if provided) -> empty string.
    """
    root_value = value if root is None else root

    if isinstance(value, dict):
        return {k: resolve_placeholders(v, root_value, env) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_placeholders(item, root_value, env) for item in value]
    if isinstance(value, str):
        def replacer(match: re.Match[str]) -> str:
            key = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""

            if key in env:
                return env[key]

            root_match = _get_value_from_path(root_value, key)
            if root_match is not None:
                return "" if root_match is None else str(root_match)

            return default if match.group(2) is not None else ""

        return _PLACEHOLDER_PATTERN.sub(replacer, value)

    return value


class Config:
    """Flexible configuration loader with singleton pattern and advanced features.
    
    Features:
    - Singleton pattern for consistent config access
    - Load multiple JSON/YAML files from config directory
    - Environment variable resolution (${VAR_NAME} syntax)
    - Auto-create directories defined in config
    - Dot notation access (e.g., 'database.host')
    - Type-safe path handling
    """
    
    _instance = None
    _config = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure single config instance."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config_dir: str | Path = "config", auto_create_dirs: bool = True):
        """Initialize configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
            auto_create_dirs: Auto-create directories from 'paths' config
        """
        if self._config is None:
            self.config_dir = Path(config_dir)
            self.auto_create_dirs = auto_create_dirs
            self._load_config()
            if self.auto_create_dirs:
                self._create_directories()
    
    def _load_config(self):
        """Load and merge all configuration files from config directory."""
        if not self.config_dir.exists():
            # Don't raise error, just initialize empty config
            self._config = {}
            return
        
        # Load all JSON and YAML files from config directory
        self._config = {}
        config_files = sorted(
            list(self.config_dir.glob('*.json')) +
            list(self.config_dir.glob('*.yaml')) +
            list(self.config_dir.glob('*.yml')) +
            list(self.config_dir.glob('*.toml')) +
            list(self.config_dir.glob('*.ini')) +
            list(self.config_dir.glob('*.conf'))
        )
        
        # Merge all config files
        for config_file in config_files:
            file_config = self._load_file(config_file)
            if file_config:
                self._merge_config(self._config, file_config)
        
        # Replace environment variable placeholders
        self._config = resolve_placeholders(self._config, root=self._config, env=os.environ)
    
    def _load_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a single configuration file (json, yaml, toml, ini/conf)."""
        try:
            if file_path.suffix == '.json':
                return json.loads(file_path.read_text())
            if file_path.suffix in {'.yaml', '.yml'}:
                return yaml.safe_load(file_path.read_text()) or {}
            if file_path.suffix == '.toml':
                if tomllib is None:
                    print("Warning: tomllib not available; skipping toml load")
                    return {}
                return tomllib.loads(file_path.read_text())
            if file_path.suffix in {'.ini', '.conf'}:
                parser = configparser.ConfigParser()
                parser.read(file_path)
                return {section: dict(parser.items(section)) for section in parser.sections()}
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")
            return {}
    
    def _merge_config(self, base: Dict, update: Dict) -> None:
        """Recursively merge update dict into base dict.
        
        Args:
            base: Base configuration dictionary (modified in place)
            update: Configuration to merge into base
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    @staticmethod
    def _resolve_env_vars(config: Any) -> Any:
        """Resolve ${VAR} placeholders using env-first lookup with config fallback."""
        return resolve_placeholders(config, root=config, env=os.environ)
    
    def _create_directories(self):
        """Create all required directories from config.
        
        Looks for 'paths' section in config and creates all directories.
        """
        paths_config = self.get('paths', {})
        
        def create_dirs_recursive(obj):
            """Recursively find and create all path directories."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and ('dir' in key.lower() or 'path' in key.lower()):
                        Path(value).mkdir(parents=True, exist_ok=True)
                    else:
                        create_dirs_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, str):
                        Path(item).mkdir(parents=True, exist_ok=True)
        
        create_dirs_recursive(paths_config)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to config value (e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
            
        Examples:
            >>> config.get('application.name')
            'My Application'
            >>> config.get('database.port', 5432)
            5432
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_path(self, key_path: str, default: Optional[str] = None) -> Path:
        """Get a path configuration as Path object.
        
        Args:
            key_path: Dot-separated path to config value
            default: Default path string if key not found
            
        Returns:
            Absolute Path object
        """
        path_str = self.get(key_path, default)
        if path_str is None:
            return Path()
        return Path(path_str).absolute()
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration dictionary."""
        return self._config.copy()
    
    def set(self, key_path: str, value: Any) -> None:
        """Set a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to config value
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def reload(self):
        """Reload configuration from all files in config directory."""
        self._config = None
        self._load_config()
        if self.auto_create_dirs:
            self._create_directories()
    
    def list_config_files(self) -> List[str]:
        """List all configuration files loaded."""
        if self.config_dir.exists():
            files = (
                list(self.config_dir.glob('*.json')) +
                list(self.config_dir.glob('*.yaml')) +
                list(self.config_dir.glob('*.yml')) +
                list(self.config_dir.glob('*.toml')) +
                list(self.config_dir.glob('*.ini')) +
                list(self.config_dir.glob('*.conf'))
            )
            return [f.name for f in sorted(files)]
        return []
    
    def has(self, key_path: str) -> bool:
        """Check if a configuration key exists.
        
        Args:
            key_path: Dot-separated path to config value
            
        Returns:
            True if key exists, False otherwise
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return False
        
        return True
    
    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access to config values."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Dictionary-style setting of config values."""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists using 'in' operator."""
        return self.has(key)


def load_config_file(config_dir: str | Path, filename: str = "settings") -> Dict[str, Any]:
    """Load a single config file (yaml/yml/json/toml/ini/conf) if present.

    Search order: yaml, yml, json, toml, ini, conf. Returns empty dict if none.
    """
    cfg_dir = Path(config_dir)
    candidates = [
        cfg_dir / f"{filename}.yaml",
        cfg_dir / f"{filename}.yml",
        cfg_dir / f"{filename}.json",
        cfg_dir / f"{filename}.toml",
        cfg_dir / f"{filename}.ini",
        cfg_dir / f"{filename}.conf",
    ]

    for path in candidates:
        if path.is_file():
            if path.suffix in {".yaml", ".yml"}:
                return yaml.safe_load(path.read_text()) or {}
            if path.suffix == ".json":
                return json.loads(path.read_text())
            if path.suffix == ".toml" and tomllib:
                return tomllib.loads(path.read_text())
            if path.suffix in {".ini", ".conf"}:
                parser = configparser.ConfigParser()
                parser.read(path)
                return {section: dict(parser.items(section)) for section in parser.sections()}
    return {}


def load_all_config_files(config_dir: str | Path) -> Dict[str, Any]:
    """Load and merge all JSON and YAML files from a directory.
    
    Args:
        config_dir: Directory containing configuration files
        
    Returns:
        Merged configuration dictionary with env var resolution
    """
    cfg_dir = Path(config_dir)
    if not cfg_dir.exists():
        return {}
    
    config = {}
    config_files = sorted(
        list(cfg_dir.glob('*.json')) +
        list(cfg_dir.glob('*.yaml')) +
        list(cfg_dir.glob('*.yml')) +
        list(cfg_dir.glob('*.toml')) +
        list(cfg_dir.glob('*.ini')) +
        list(cfg_dir.glob('*.conf'))
    )
    
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix == '.json':
                    file_config = json.load(f)
                elif config_file.suffix in {'.yaml', '.yml'}:
                    file_config = yaml.safe_load(f) or {}
                elif config_file.suffix == '.toml' and tomllib:
                    file_config = tomllib.load(f)
                elif config_file.suffix in {'.ini', '.conf'}:
                    parser = configparser.ConfigParser()
                    parser.read_file(f)
                    file_config = {section: dict(parser.items(section)) for section in parser.sections()}
                else:
                    continue
                
                # Merge into main config
                _merge_dicts(config, file_config)
        except Exception as e:
            print(f"Warning: Failed to load {config_file}: {e}")
    
    return Config._resolve_env_vars(config)


def _merge_dicts(base: Dict, update: Dict) -> None:
    """Recursively merge update dict into base dict."""
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _merge_dicts(base[key], value)
        else:
            base[key] = value


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


# Global configuration instance (singleton)
config = Config()


__all__ = [
    'Config',
    'config',
    'load_config_file',
    'load_all_config_files',
    'load_settings',
    'resolve_placeholders',
]
