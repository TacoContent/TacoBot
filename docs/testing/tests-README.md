# Test Suite Scaffolding

This directory will contain unit (and potentially integration) tests for TacoBot.

## Conventions

- Place pure unit tests in files named `test_<area>.py`.
- Use `conftest.py` for shared fixtures (e.g., event loop, mock Discord client, temp Mongo, etc.).
- Prefer fast, deterministic tests; network and external API calls should be mocked.

## Suggested Fixture Ideas (add when needed)

- `event_loop` (asyncio) for async handlers.
- `mock_settings` returning an in-memory Settings-like object.
- `discord_client` mock for command/cog tests.
- `http_client` leveraging an in-process test server (future addition).

## Running Tests (once dependencies added)

```bash
pytest -q
```

No actual tests are included yet (per initial scaffolding request).
