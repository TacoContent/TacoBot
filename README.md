# TacoBot

![OpenAPI Coverage](docs/badges/openapi-coverage.svg)

TacoBot is a feature-rich, modular Discord bot designed to enhance your server with a wide range of community, moderation, automation, and fun features. It supports advanced metrics, integrations, and custom automations to help manage and grow your Discord community.

## Features

- Modular cogs for easy feature management
- Extensive command set for users and admins
- MongoDB-backed data storage and analytics
- Prometheus metrics exporter for monitoring
- Node-RED integration for automation and external service hooks
- Support for games, events, suggestions, and more

## Getting Started

To get started with TacoBot, clone this repository and review the documentation for setup, configuration, and usage instructions.

## Quickstart

The fastest way to get TacoBot running locally (Linux/macOS bash or Windows PowerShell 7+):

```bash
git clone https://github.com/your-org/TacoBot.git
cd TacoBot
python3 -m venv .venv && source .venv/scripts/activate  # (PowerShell: python -m venv .venv; . .venv/Scripts/Activate.ps1)
pip install -e .
python ./main.py
```

If you prefer Docker, skip to the [Docker](#docker) section below.

## Environment Setup (Python Virtual Environment)

TacoBot now ships with a `pyproject.toml` (PEP 621) for modern dependency management.
Use this preferred workflow to create an isolated environment and install dependencies.

### 1. Prerequisites

- Python >=3.10–3.12 (see `requires-python` in `pyproject.toml`)
- (Recommended) Latest `pip` and `virtualenv` tooling

### 2. Create & Activate a Virtual Environment

#### Windows (PowerShell)

``` pwsh
python -m venv .venv
. .venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
```

#### Linux / macOS (bash / zsh)

``` bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Install Project Dependencies (Editable Mode)

This installs the application and its runtime dependencies defined in `pyproject.toml`:

``` shell
pip install -e .
```

### 4. (Alternative) Install from Legacy Requirements File

If you prefer the classic approach:

``` shell
pip install -r setup/requirements.txt
```

### 5. Verifying the Installation

``` shell
python -c "import discord, pymongo, aiohttp; print('Dependencies OK')"
```

### 6. (Optional) Development Tooling

If/when a `dev` extra is added you could install with:

``` shell
pip install -e .[dev]
```

### 7. Running the Bot

After configuring environment variables (.env) / settings:

``` shell
python ./main.py
```

To deactivate the virtual environment when finished:

``` pwsh
deactivate
```

## Docker

You can run TacoBot in a container. The provided `Dockerfile` builds an image using the project sources.

### 1. Build the Image

```bash
docker build -t tacobot:latest .
```

### 2. Provide Environment Configuration

Create a `.env` file (or export variables) containing at least your Discord bot token and Mongo connection string, for example:

```env
DISCORD_TOKEN=your_bot_token_here
MONGODB_URI=mongodb://mongo:27017/tacobot
```

### 3. Run the Container

Expose the HTTP port (adjust if your server component uses a different port):

```bash
docker run --env-file .env -p 8931:8931 -p 8932:8932 --name tacobot tacobot:latest
```

### 4. Persisting Data (Optional)

If the bot writes files (logs, cache, etc.) map a volume:

```bash
docker run --env-file .env -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --name tacobot tacobot:latest
```

### 5. Updating

Pull latest changes, rebuild, and recreate the container:

```bash
git pull
docker build -t tacobot:latest .
docker stop tacobot && docker rm tacobot
docker run --env-file .env -p 8000:8000 --name tacobot tacobot:latest
```

## Bootstrap Scripts

For convenience, platform-specific scripts are included under `scripts/` to create/activate a virtual environment and install dependencies.

| Platform | Script |
|----------|--------|
| Windows (PowerShell) | `scripts/bootstrap.ps1` |
| Linux | `scripts/bootstrap-linux.sh` |
| macOS | `scripts/bootstrap-macos.sh` |

### Usage Examples

Windows (PowerShell):

```pwsh
./scripts/bootstrap.ps1
```

Linux:

```bash
chmod +x scripts/bootstrap-linux.sh
./scripts/bootstrap-linux.sh
```

macOS:

```bash
chmod +x scripts/bootstrap-macos.sh
./scripts/bootstrap-macos.sh
```

After running a bootstrap script, activate the environment (if not already active) and launch:

```bash
python ./main.py
```

## Documentation

Comprehensive documentation is available in the [docs/](./docs/README.md) folder, including:

- Feature and cog documentation
- Command reference
- Database schemas
- Metrics and monitoring
- Node-RED automation flows

For detailed guides and tables of contents, see the [TacoBot Documentation Index](./docs/README.md).

---

For questions, issues, or contributions, please refer to the documentation or open an issue in this repository.

### OpenAPI / Swagger Sync (`scripts/swagger_sync.py`)

Handler HTTP endpoints embed minimal OpenAPI fragments inside their docstrings between `>>>openapi` / `<<<openapi` markers.
The `scripts/swagger_sync.py` utility keeps those fragments and the canonical `.swagger.v1.yaml` file in sync.

Quick check (no write) using defaults:

```pwsh
python scripts/swagger_sync.py --check --handlers-root bot/lib/http/handlers/ --swagger-file .swagger.v1.yaml
```

Apply changes to the swagger file:

```pwsh
python scripts/swagger_sync.py --fix --handlers-root bot/lib/http/handlers/ --swagger-file .swagger.v1.yaml
```

Method-rooted blocks (multiple verbs in one docstring) are supported using top-level `get:`, `post:` etc. keys.
Custom delimiters can be provided with `--openapi-start` / `--openapi-end` if you need a different embedding style.
If a docstring lists a verb that's not present in the decorator's `method=` list you can:

- Run normally (default) – a warning is emitted and the extraneous verb is ignored.
- Use `--strict` – the run fails fast (non-zero exit) so CI can catch stale / copy-pasted verb sections.

Example strict run:

```pwsh
python scripts/swagger_sync.py --check --strict --handlers-root bot/lib/http/handlers/ --swagger-file .swagger.v1.yaml
```

See `tests/test_swagger_sync_method_rooted.py` and `tests/test_swagger_sync_strict_validation.py` for examples.

## Contributing / Running Tests

### Development Environment

Create and activate a virtual environment, then install the project with dev dependencies:

```pwsh
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -e .[dev]
```

On Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Running the Test Suite

Plain run:

```bash
pytest
```

With coverage (terminal report):

```bash
pytest --cov=bot --cov-report=term-missing
```

### Using VS Code Tasks

This repo includes `.vscode/tasks.json` tasks:

| Task | Description |
|------|-------------|
| Python: Run Tests | Executes all tests with pytest. |
| Python: Run Tests (Coverage) | Runs tests and prints line coverage. |
| Lint (Ruff) | Static style / lint checks. |
| Type Check (mypy) | Static type analysis. |

Open the command palette and run: `Tasks: Run Task`.

### Pre-Commit (Optional Recommendation)

You can add a local pre-commit hook to run lint + tests before commits:

```bash
echo "#!/usr/bin/env bash
ruff check . || exit 1
mypy bot || exit 1
pytest -q || exit 1" > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Filing Issues / PRs

1. Open an issue describing the change or bug.
2. Create a feature branch (`feat/short-description`).
3. Add tests for new behavior; ensure `pytest` passes.
4. Run lint and type checks.
5. Submit PR with a concise summary and link to the issue.

### Coding Guidelines

- Follow existing 4-space indentation & formatting (Black enforced).
- Keep public APIs documented with docstrings.
- Favor small focused commits for review clarity.
- Maintain consistent error payload shape (`{"error": "message"}`).

Thank you for contributing to TacoBot!
