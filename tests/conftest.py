"""Shared pytest fixtures for all test modules.

This conftest.py provides session and module-scoped fixtures to reduce
test initialization overhead and improve overall test suite performance.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


# ==============================================================================
# Session-scoped fixtures (created once per test session)
# ==============================================================================


@pytest.fixture(scope="session")
def session_bot():
    """Session-scoped mock bot to reuse across all tests."""
    return MagicMock()


# ==============================================================================
# Module-scoped fixtures (created once per test module)
# ==============================================================================


@pytest.fixture(scope="module")
def module_settings():
    """Module-scoped mock settings object."""
    s = MagicMock()
    s.get_settings = MagicMock(return_value={})
    s.get_string = MagicMock(return_value="Test string")
    s.name = "TacoBot"
    s.version = "1.0.0"
    s.log_level = "debug"
    s.settings_db = MagicMock()
    s.settings_db.set_setting = MagicMock()
    return s


# ==============================================================================
# Function-scoped fixtures (created once per test function - default)
# ==============================================================================


@pytest.fixture
def bot():
    """Function-scoped mock bot instance."""
    return MagicMock()


@pytest.fixture
def invites_db():
    """Function-scoped mock invites database."""
    db = MagicMock()
    db.track_invite_code = MagicMock()
    return db


@pytest.fixture
def settings():
    """Function-scoped mock settings object."""
    s = MagicMock()
    s.get_settings = MagicMock(return_value={})
    s.get_string = MagicMock(return_value="Test string")
    s.name = "TacoBot"
    s.version = "1.0.0"
    s.log_level = "debug"
    s.settings_db = MagicMock()
    s.settings_db.set_setting = MagicMock()
    return s


@pytest.fixture
def messaging():
    """Function-scoped mock messaging instance with async methods."""
    m = MagicMock()
    m.send_embed = AsyncMock()
    m.notify_of_error = AsyncMock()
    return m


@pytest.fixture
def tacos_db():
    """Function-scoped mock tacos database."""
    db = MagicMock()
    db.get_tacos_count = MagicMock(return_value=0)
    db.remove_tacos = MagicMock()
    db.add_taco_gift = MagicMock()
    db.get_total_gifted_tacos = MagicMock(return_value=0)
    return db


@pytest.fixture
def tracking_db():
    """Function-scoped mock tracking database."""
    db = MagicMock()
    db.track_command_usage = MagicMock()
    db.track_discord_user = MagicMock()
    db.track_system_action = MagicMock()
    return db


@pytest.fixture
def announcements_db():
    """Function-scoped mock announcements database."""
    db = MagicMock()
    db.track_announcement = MagicMock()
    return db


@pytest.fixture
def twitch_db():
    """Function-scoped mock Twitch database."""
    db = MagicMock()
    db.link_twitch_to_discord_from_code = MagicMock(return_value=True)
    db.set_twitch_discord_link_code = MagicMock(return_value=True)
    db.get_user_twitch_info = MagicMock(return_value=None)
    db.set_user_twitch_info = MagicMock()
    return db


@pytest.fixture
def live_db():
    """Function-scoped mock live database."""
    db = MagicMock()
    db.get_tracked_live = MagicMock(return_value=[])
    db.get_tracked_live_by_user = MagicMock(return_value=[])
    db.track_live = MagicMock()
    db.track_live_activity = MagicMock()
    db.untrack_live = MagicMock()
    return db


@pytest.fixture
def role_helper():
    """Function-scoped mock role helper with async methods."""
    h = MagicMock()
    h.add_remove_roles = AsyncMock()
    return h


@pytest.fixture
def permissions():
    """Function-scoped mock permissions handler."""
    p = MagicMock()
    p.has_taco_permission = MagicMock(return_value=False)
    return p


@pytest.fixture
def entity_helper():
    """Function-scoped mock entity helper."""
    h = MagicMock()
    h.get_or_fetch_channel = AsyncMock()
    h.get_or_fetch_member = AsyncMock()
    return h


@pytest.fixture
def taco_helper():
    """Function-scoped mock taco helper."""
    return MagicMock()


@pytest.fixture
def message_helper():
    """Function-scoped mock message helper with async methods."""
    h = MagicMock()
    h.notify_bot_not_initialized = AsyncMock()
    return h


@pytest.fixture
def prompt_helper():
    """Function-scoped mock prompt helper with async methods."""
    h = MagicMock()
    h.ask_yes_no = AsyncMock()
    return h
