# utils-api

Shared utilities for API services (structured logging, configuration loading). Designed to be installed as a dependency in other services.

## Features
- Structured logging with JSON output and correlation-id support
- Simple logging bootstrap helper for FastAPI/CLI apps
- Config loader that merges config folder files (YAML/JSON) with environment variables and optional .env

## Install
```bash
pip install -e .
```
Or as a relative dependency from another service’s `requirements.txt`:
```
-e ../utils-api
```

## Usage

### Structured logging
```python
from utils_api.logging import setup_logging

logger = setup_logging(service_name="entity-api", level="INFO")
logger.info("service started", extra={"correlation_id": "abc-123"})
```

### Config loading
```python
from pydantic_settings import BaseSettings
from utils_api.config import load_settings

class Settings(BaseSettings):
    database_url: str
    log_level: str = "INFO"

settings = load_settings(Settings, config_dir="config", env_file=".env")
```
- If `config/settings.yaml` (or `.yml` / `.json`) exists, its values are loaded first.
- Environment variables override file values (standard `BaseSettings` behavior).
- Optional `_env_file` is passed through for `.env` support.

## Tests
```bash
pip install -e .[dev]
pytest tests -v
```

## Included modules
- `utils_api.logging`: JSON logging setup helper
- `utils_api.config`: Config loader that supports config directory + env merges
