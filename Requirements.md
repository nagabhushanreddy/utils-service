
# Multi-Finance User Application  
## Microservices Requirements Document (OpenAPI-Compliant)

---

## 1. Overview

This document defines the functional and non-functional requirements for a **Multi-Finance User Web Application** built using a **microservices REST architecture**.  
All services **MUST expose OpenAPI 3.x compliant specifications**.

### Core Domains
- User & Identity
- Authorization
- User Profile
- Loan Management

---

## 2. Architecture Principles

- Microservices with **single responsibility**
- **Database-per-service or use entity-service**
- REST APIs with **OpenAPI 3.0+**
- Stateless services
- JWT-based security
- Event-driven integration where applicable
- Default **DENY** authorization model

---

## 3. Services Overview

| Service | Responsibility |
|------|---------------|
| API Gateway / BFF | Single entry point, auth enforcement |
| Entity Service | CRUD Operations & Database Interactions |
| Identity & Authentication Service | Login, OTP, token issuance |
| Authorization Service | Central policy decision (RBAC + ABAC) |
| User Profile Service | Customer profile & KYC metadata |
| Loan Service | Loan products, applications, accounts |
| Document Service | KYC & loan document storage |
| Notification Service | Email/SMS orchestration |
| Audit & Compliance Service | Immutable audit logging |
| **Utils Service** ⭐ | **Shared utilities for configuration and logging** |

---

## 4. Utils Service

A shared utility library for microservices providing standardized configuration loading and structured logging capabilities. Designed to be imported as a dependency by other services for code reusability.

## Features

- **Structured Logging**: JSON-formatted logs with correlation ID support
- **Configuration Management**: Unified config loading from YAML/JSON files with environment variable overrides
- **Lazy Initialization**: Efficient initialization pattern that avoids circular dependencies
- **Singleton Pattern**: Ensures single instances of logger and config across application
- **Library Mode**: Importable package for other microservices
- **Environment Variable Support**: Automatic merging of file-based config with env vars
- **Flexible Config Directory**: Custom config directory support per service
- **Type Safety**: Type-safe configuration with Pydantic validation
- **Easy Integration**: Simple import and use pattern for consuming services

## Architecture

### Shared Utility Design

This service follows a **library pattern** where utilities are imported by other services:

```
Service Structure:
├── utils/
│   ├── __init__.py (exports logger, config, init_utils)
│   ├── logger.py (Logger singleton with lazy initialization)
│   └── config.py (Config singleton with file + env merging)
├── tests/
│   ├── test_logger.py
│   └── test_config.py
└── config/ (example config for testing)
```

**Benefits:**
- ✅ Consistent logging across all services
- ✅ Unified configuration pattern
- ✅ Reduced code duplication
- ✅ Easy to update and maintain centrally
- ✅ Type-safe configuration loading
- ✅ No initialization order issues

### OpenAPI Requirements
- Versioned paths `/api/v1`
- OAuth2 / Bearer JWT security scheme
- Correlation-Id header propagation

---

### 4.1 Scope
Shared utilities for configuration management and structured logging across all microservices.

### 4.2 Technology Stack
- **Language**: Python 3.10+
- **Configuration**: pydantic-settings (type-safe settings)
- **Config Formats**: YAML, JSON support via pyyaml and tomli
- **Logging**: python-json-logger for structured JSON logs
- **Data Validation**: Pydantic for type safety
- **Testing**: pytest with coverage reporting
- **Package Management**: setuptools for pip installable package

### 4.3 Core APIs/Modules

### Configuration Module (`utils.config`)

#### Load Settings Function
**Purpose**: Load type-safe configuration from files and environment variables

**Input Requirements:**
- Pydantic BaseSettings class for type validation
- Config directory path (optional, default: "config")
- Environment file path (optional)

**Behavior:**
- Must automatically load YAML/JSON files from specified config directory
- Must merge with environment variables (env vars take precedence)
- Must support optional .env file loading
- Must perform type validation via Pydantic
- Must return validated settings instance

**Features Required:**
- Singleton pattern for efficiency
- Support for nested configuration structures
- Default value handling
- Clear error messages for missing required fields

#### Config Singleton
**Purpose**: Global configuration accessor

**Required Capabilities:**
- Set custom config directory per service
- Reload configuration on demand
- Get configuration values with default fallback
- Set configuration values at runtime
- Thread-safe access

### Logging Module (`utils.logger`)

#### Setup Logging Function
**Purpose**: Initialize structured JSON logger for a service

**Input Requirements:**
- Service name (required)
- Log level (optional, default: "INFO")

**Output Requirements:**
- Return configured logger instance
- Logger must output JSON format
- Must support standard log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Log Format Requirements:**
- Timestamp in ISO 8601 format
- Log level field
- Service name field
- Message field
- Support for additional structured fields via extra parameter
- Correlation ID field when provided
- Exception stack traces when exc_info is True

**Example Expected Output:**
- Timestamp: "2026-01-10T10:30:00.000Z"
- Level: "INFO", "ERROR", etc.
- Service: Service identifier
- Message: Log message text
- Additional fields: Correlation ID, user ID, duration, etc.

#### Logger Singleton
**Purpose**: Global logger instance with lazy initialization

**Required Capabilities:**
- Lazy initialization (created on first access)
- Standard logging methods: info(), error(), warning(), debug(), critical()
- Support for structured data via extra parameter
- Support for exception logging with stack traces
- Thread-safe access
- Reset capability for testing

### Initialization Module (`utils.init_utils`)

#### Initialization Function
**Purpose**: Initialize utilities with proper configuration loading order

**Input Requirements:**
- Config directory path (optional, default: "config")

**Behavior Requirements:**
- Must load configuration before logger initialization
- Must ensure logger uses values from loaded config
- Must prevent circular dependency issues
- Must ensure proper initialization order
- Must be idempotent (safe to call multiple times)

**Expected Initialization Sequence:**
1. Load configuration from specified directory
2. Apply environment variable overrides
3. Initialize logger with config values (log level, format)
4. Make both config and logger available for use

**Usage Context:**
- Should be called at application startup
- Should be called before accessing logger or config
- Recommended for all services using utils

### 4.4 Functional Requirements

#### 4.4.1 Configuration Management
- **Multi-format support**
  - Load configuration from YAML files (`.yaml`, `.yml`)
  - Load configuration from JSON files (`.json`)
  - Support for TOML files via tomli
  - Environment variable override support
  - Optional .env file loading

- **Type Safety**
  - Pydantic BaseSettings integration
  - Type validation on load
  - Required field enforcement
  - Default value support

- **Config Merging**
  - File-based config loaded first
  - Environment variables override file values
  - .env file values applied if specified
  - Priority: .env < config files < environment variables

- **Singleton Pattern**
  - Single Config instance per application
  - Thread-safe access
  - Reload capability for testing
  - Reset capability for test isolation

#### 4.4.2 Structured Logging
- **JSON Format**
  - All logs output as JSON objects
  - Consistent field naming across services
  - Parseable by log aggregation tools
  - Machine-readable format

- **Standard Fields**
  - `timestamp`: ISO 8601 format
  - `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - `service`: Service name identifier
  - `message`: Log message text
  - `correlation_id`: Request correlation ID (optional)

- **Correlation ID Support**
  - Automatic correlation ID propagation
  - Extract from request headers
  - Include in all log entries
  - Support for distributed tracing

- **Log Levels**
  - DEBUG: Detailed debugging information
  - INFO: General informational messages
  - WARNING: Warning messages for unexpected behavior
  - ERROR: Error messages for failures
  - CRITICAL: Critical errors requiring immediate attention

- **Performance**
  - Lazy initialization to avoid overhead
  - Efficient JSON serialization
  - Minimal performance impact
  - Configurable log levels to control verbosity

#### 4.4.3 Library Integration
- **Easy Import**
  - Simple import pattern: `from utils import logger, config`
  - No complex setup required
  - Works with relative path imports
  - Can be installed via pip -e

- **Dependency Management**
  - Installable via pip
  - Relative path installation support: `-e ../utils-service`
  - Proper package metadata (pyproject.toml)
  - Minimal external dependencies

- **Service Isolation**
  - Each service can have custom config directory
  - Logger reset capability for testing
  - No shared state between services
  - Independent configuration per service

### 4.5 Non-Functional Requirements

#### 4.5.1 Performance
- **Latency Targets**
  - Config loading: < 100ms
  - Logger initialization: < 50ms
  - Log entry creation: < 5ms
  - Config value access: < 1ms

- **Memory Efficiency**
  - Singleton pattern to minimize instances
  - Lazy initialization to defer overhead
  - Efficient JSON serialization
  - Minimal memory footprint

#### 4.5.2 Reliability
- **Error Handling**
  - Graceful handling of missing config files
  - Default values for missing configuration
  - Clear error messages for validation failures
  - No silent failures

- **Thread Safety**
  - Thread-safe singleton access
  - Safe concurrent config access
  - Safe concurrent logging

#### 4.5.3 Observability
- **Logging**
  - Self-descriptive log format
  - Clear error messages
  - Stack traces on errors
  - Context preservation

- **Testing Support**
  - Reset methods for test isolation
  - Mock-friendly design
  - Clear initialization state
  - Reproducible behavior

#### 4.5.4 Data Formats
- **Configuration Files**
  - YAML: Primary format (human-readable)
  - JSON: Alternative format (machine-friendly)
  - TOML: Optional format support
  - .env: Environment file support

- **Log Format**
  - JSON Lines format (one JSON per line)
  - UTF-8 encoding
  - ISO 8601 timestamps
  - Consistent field types

### 4.6 Service Dependencies

#### 4.6.1 External Dependencies
**Required Python packages**

Core dependencies:
- `pydantic-settings>=2.1.0` - Type-safe settings management
- `pyyaml>=6.0` - YAML parsing
- `tomli>=2.0.1` - TOML parsing (Python < 3.11)
- `python-json-logger>=2.0.0` - Structured JSON logging

Development dependencies:
- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `black>=23.0.0` - Code formatting
- `mypy>=1.5.0` - Type checking

#### 4.6.2 No Runtime Service Dependencies
This is a **library service** with no external service dependencies:
- No database required
- No API calls to other services
- No network dependencies
- Pure utility functions

### 4.7 Usage Specifications

#### 4.7.1 Installation Methods

**Method 1: Relative Path Install (Development)**
```bash
# From another service's directory
pip install -e ../utils-service
```

**Method 2: requirements.txt Reference**
```txt
# In another service's requirements.txt
-e ../utils-service
```

**Method 3: Direct pip install**
```bash
# If packaged and published
pip install utils-service
```

#### 4.7.2 Import Patterns

**Simple Import Pattern Requirements:**
- Must support importing logger, config, and init_utils from main utils package
- Must allow initialization with config directory parameter
- Must make logger and config immediately usable after initialization
- Logger and config must be accessible throughout application after init

**Advanced Custom Config Pattern Requirements:**
- Must support setting custom config directory per service
- Must support reloading configuration after directory change
- Must support resetting logger to use new config
- Must allow getting fresh logger instance with updated config

**Direct Module Access Pattern Requirements:**
- Must support importing specific functions directly from submodules
- Must allow explicit control over initialization parameters
- Must support setup_logging with service name and level parameters
- Must support load_settings with Settings class and config directory
- Must work independently of singleton pattern

#### 4.7.3 Configuration File Format

**YAML Format Requirements:**
- Must support standard YAML syntax
- Must support nested structures for grouping related config
- Must support comments for documentation
- Common fields: service_name, port, log_level
- Must support database configuration section
- Must support feature flags section

**JSON Format Requirements:**
- Must support standard JSON syntax
- Must support nested objects for hierarchical config
- Common fields: service_name, port, log_level
- Must support database configuration object
- Must support boolean values for feature flags

**Environment Variable Override Requirements:**
- Must support overriding any config file value
- Must use uppercase naming convention
- Must support nested config with double underscore separator
- Example mappings:
  - service_name → SERVICE_NAME
  - port → PORT
  - database.host → DATABASE__HOST
- Environment variables must take precedence over file values

### 4.8 Testing Requirements

#### 4.8.1 Unit Tests
- Config loading from YAML files
- Config loading from JSON files
- Environment variable overrides
- Logger initialization
- JSON log formatting
- Correlation ID propagation
- Singleton behavior
- Reset and reload functionality

#### 4.8.2 Integration Tests
- Config + Logger integration
- Multiple services using same utils
- Config directory customization
- Environment variable merging
- .env file loading

#### 4.8.3 Coverage & Reporting
- Minimum 80% code coverage
- XML test reports (JUnit format)
- HTML coverage reports
- Test execution logs

#### 4.8.4 Test Framework
- pytest (Python testing framework)
- pytest-cov (coverage reporting)
- Mocking for file system operations
- Fixtures for test isolation

### 4.9 Configuration Management

#### 4.9.1 Environment Variables
```
# Service defaults (can be overridden by consuming services)
LOG_LEVEL=INFO
CONFIG_DIR=config
ENABLE_JSON_LOGS=true
LOG_CORRELATION_ID=true
```

#### 4.9.2 Package Configuration

**pyproject.toml:**
```toml
[project]
name = "utils-service"
version = "1.0.0"
description = "Shared utilities for configuration and logging"
requires-python = ">=3.10"

dependencies = [
    "pydantic-settings>=2.1.0",
    "pyyaml>=6.0",
    "tomli>=2.0.1",
    "python-json-logger>=2.0.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "mypy>=1.5.0"
]
```

### 4.10 Deployment Architecture

#### 4.10.1 Library Distribution
**Installation Methods Required:**
- Editable mode installation for development
- Installation with optional dev dependencies
- Distribution package building capability
- Support for pip install from relative path
- Support for pip install from requirements.txt reference

**Package Requirements:**
- Must be installable via pip
- Must support editable installs (-e flag)
- Must declare optional dev dependency group
- Must include proper package metadata

#### 4.10.2 Service Integration
**Integration Requirements:**
- Must be importable in consuming service's entry point
- Must support initialization at application startup
- Initialization must complete before application logic
- Logger and config must be available after initialization
- Must work with FastAPI, Flask, or any Python framework

**Integration Pattern:**
- Import init_utils, logger, and config
- Call init_utils with config directory
- Access logger and config throughout application

#### 4.10.3 Testing
**Test Execution Requirements:**
- Must support pytest test discovery
- Must support verbose output mode
- Must support coverage reporting (HTML and XML formats)
- Must support running all tests or specific test files
- Must support running tests from command line
- Must generate coverage reports in reports/ directory

### 4.11 Acceptance Criteria
- [ ] Config loading from YAML/JSON functional
- [ ] Environment variable override working
- [ ] Structured JSON logging operational
- [ ] Correlation ID support implemented
- [ ] Singleton pattern working correctly
- [ ] Init pattern prevents initialization issues
- [ ] Test coverage >= 80%
- [ ] All error cases handled gracefully
- [ ] Documentation complete and clear
- [ ] Successfully integrated in at least 2 services
- [ ] Performance targets met
- [ ] Thread-safety verified

---

## 5. Cross-Cutting Requirements

### 5.1 Observability & Monitoring
- **Structured Logging**: JSON format with correlation ID propagation
- **Self-Monitoring**: Utils service logs its own initialization
- **Clear Error Messages**: Descriptive errors for config/logging issues
- **Testing Support**: Easy to mock and test in consuming services

### 5.2 Code Quality Standards
- **Type Hints**: All functions have type annotations
- **Documentation**: Docstrings for all public functions
- **Code Style**: Black formatting, isort for imports
- **Type Checking**: mypy validation passes

### 5.3 Testing & Quality
- **Test-Driven Development**: Unit tests for all functionality
- **Code Coverage**: Minimum 80% coverage requirement
- **Test Reports**: XML (JUnit) and HTML formats
- **Test Frameworks**: pytest with pytest-cov

### 5.4 Library Design Principles
- **Single Responsibility**: Config and logging only
- **No Side Effects**: No global state pollution
- **Easy Integration**: Simple import and use
- **Backward Compatibility**: Version updates don't break consumers
- **Minimal Dependencies**: Keep dependency footprint small

### 5.5 Documentation Requirements
- **README.md**: Installation, basic usage, features
- **USAGE_GUIDE.md**: Detailed usage patterns and examples
- **Requirements.md**: This document - complete specifications
- **Docstrings**: All public APIs documented
- **Examples**: Working code examples for all features

### 5.6 Project Structure

**Standard Utils Service Structure:**

```
utils-service/
├── utils/                      # Main package
│   ├── __init__.py            # Exports logger, config, init_utils
│   ├── logger.py              # Logger singleton with lazy init
│   └── config.py              # Config singleton with file loading
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── test_logger.py         # Logger tests
│   ├── test_config.py         # Config tests
│   └── test_integration.py    # Integration tests
├── config/                    # Example config for testing
│   └── settings.yaml
├── pyproject.toml            # Package configuration
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
├── README.md                 # Service documentation
├── USAGE_GUIDE.md           # Detailed usage guide
├── Requirements.md          # This file
└── run_tests.py             # Test runner script
```

**Standards:**
- Keep package structure flat and simple
- All public APIs exported from `__init__.py`
- Clear separation of concerns (logger vs config)
- Comprehensive test coverage
- Example configs for reference

---

## 6. Future Work / TODO Items

### 6.1 Enhanced Features (Phase 2)
- **Distributed Tracing**: OpenTelemetry integration for distributed tracing
- **Metrics Collection**: Prometheus metrics helpers
- **Advanced Logging**: Log aggregation service integration (ELK, Splunk)
- **Config Validation**: Enhanced schema validation with custom validators
- **Remote Config**: Support for remote config sources (Consul, etcd)
- **Secrets Management**: Integration with Vault/AWS Secrets Manager
- **Log Filtering**: Dynamic log level adjustment per module
- **Log Sampling**: High-volume log sampling to reduce overhead

### 6.2 Performance Improvements (Phase 2)
- **Async Logging**: Non-blocking async log writing
- **Batch Logging**: Batched log writes for high throughput
- **Log Buffering**: Configurable log buffer sizes
- **Compression**: Log compression for storage efficiency

---

**End of Document**

