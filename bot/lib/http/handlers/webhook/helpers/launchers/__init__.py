"""Launcher strategy module with automatic discovery and export.

This module automatically discovers all LauncherStrategy subclasses
and exports them for convenient importing.
"""

import inspect
import typing

from lib.http.handlers.webhook.helpers.launchers.LauncherStrategies import LauncherStrategy


# Automatically discover all LauncherStrategy subclasses
def get_launcher_strategies() -> typing.Dict[str, typing.Type[LauncherStrategy]]:
    """Dynamically find all LauncherStrategy subclasses in this module."""
    strategies = {}

    # Get all classes from LauncherStrategies module
    from . import LauncherStrategies

    for name, obj in inspect.getmembers(LauncherStrategies, inspect.isclass):
        # Check if it's a subclass of LauncherStrategy but not the base class itself
        if issubclass(obj, LauncherStrategy) and obj is not LauncherStrategy and not inspect.isabstract(obj):
            strategies[name] = obj

    return strategies


# Get all launcher strategies
_LAUNCHER_STRATEGIES = get_launcher_strategies()

# Export all strategies for convenient access
LAUNCHER_STRATEGIES = _LAUNCHER_STRATEGIES

# Build __all__ dynamically - explicit tuple for type checker
__all__ = [k for k, _ in LAUNCHER_STRATEGIES.items()]  # type: ignore[misc]
