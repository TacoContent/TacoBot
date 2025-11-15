import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from bot.lib.enums import loglevel
from bot.lib.mongodb.migration_runner import MigrationRunner


class DummySettings:
    def __init__(self, level: str = "DEBUG") -> None:
        self.log_level = level


def _make_module_with_migration(module_name: str, needs: bool = True, run_side_effect=None):
    """Create a fake migration module with a Migration class.

    run_side_effect: None or exception to raise when run called. If callable, called; else appended to list.
    """
    mod = types.ModuleType(module_name)
    calls = []

    class Migration:
        def __init__(self):
            pass

        def needs_run(self):
            return needs

        def run(self):
            if callable(run_side_effect):
                run_side_effect()
            elif isinstance(run_side_effect, Exception):
                raise run_side_effect
            else:
                calls.append(True)

    mod.Migration = Migration
    mod._calls = calls
    return mod


def test_init_collects_and_sorts_migrations(monkeypatch):
    # Setup a couple of migration filenames in shuffled order
    files = ["10_third_migration.py", "2_second_migration.py", "1_first_migration.py", "ignore.txt"]
    monkeypatch.setattr("os.listdir", lambda path: files)

    # patch logger.Log so we don't do DB work; collect call args
    with patch("bot.lib.mongodb.migration_runner.logger.Log") as MockLog:
        settings = DummySettings("INFO")
        runner = MigrationRunner(settings)

    # Runner should collect only _migration.py entries and sort by numeric prefix
    assert [m["id"] for m in runner._migrations] == [1, 2, 10]
    assert [m["name"] for m in runner._migrations] == [
        "1_first_migration",
        "2_second_migration",
        "10_third_migration",
    ]

    # Logger must be constructed with the right minimumLogLevel
    MockLog.assert_called_once()
    call_kwargs = MockLog.call_args[1]
    assert call_kwargs.get("minimumLogLevel") == loglevel.LogLevel.INFO


def test_start_migrations_runs_and_skips(monkeypatch):
    files = ["2_second_migration.py", "1_first_migration.py"]
    monkeypatch.setattr("os.listdir", lambda path: files)

    # Create fake modules and inject into sys.modules keyed by module path
    mod1_name = "bot.lib.migrations.1_first_migration"
    mod2_name = "bot.lib.migrations.2_second_migration"

    mod1 = _make_module_with_migration(mod1_name, needs=True)
    mod2 = _make_module_with_migration(mod2_name, needs=False)

    sys.modules[mod1_name] = mod1
    sys.modules[mod2_name] = mod2

    try:
        with patch("bot.lib.mongodb.migration_runner.logger.Log") as MockLog:
            settings = DummySettings("DEBUG")
            runner = MigrationRunner(settings)
            # Now run migrations
            runner.start_migrations()

        # mod1 should have had its run() executed (its _calls list appended True)
        assert bool(mod1._calls) is True
        # mod2's run should not have been executed
        assert bool(mod2._calls) is False

        # debug must be called for migrations found; ensure at least one debug
        assert MockLog.return_value.debug.called
    finally:
        # cleanup sys.modules
        sys.modules.pop(mod1_name, None)
        sys.modules.pop(mod2_name, None)


def test_start_migrations_stops_on_exception(monkeypatch):
    files = ["1_err_migration.py", "2_should_not_run_migration.py"]
    monkeypatch.setattr("os.listdir", lambda path: files)

    mod1_name = "bot.lib.migrations.1_err_migration"
    mod2_name = "bot.lib.migrations.2_should_not_run_migration"

    def raising():
        raise RuntimeError("boom")

    mod1 = _make_module_with_migration(mod1_name, needs=True, run_side_effect=RuntimeError("boom"))
    # mod2 would have been run if first didn't stop the loop; mark it to True so we can detect.
    mod2 = _make_module_with_migration(mod2_name, needs=True)

    sys.modules[mod1_name] = mod1
    sys.modules[mod2_name] = mod2

    try:
        with patch("bot.lib.mongodb.migration_runner.logger.Log") as MockLog:
            settings = DummySettings("DEBUG")
            runner = MigrationRunner(settings)
            runner.start_migrations()

        # Because mod1.run raises, runner should log an error and break the loop
        MockLog.return_value.error.assert_called()
        # mod2.run should not have been executed
        assert bool(mod2._calls) is False
    finally:
        sys.modules.pop(mod1_name, None)
        sys.modules.pop(mod2_name, None)


def test_start_migrations_no_migrations(monkeypatch):
    monkeypatch.setattr("os.listdir", lambda path: [])
    with patch("bot.lib.mongodb.migration_runner.logger.Log"):
        settings = DummySettings("DEBUG")
        runner = MigrationRunner(settings)
    # ensure no migrations found
    assert runner._migrations == []
