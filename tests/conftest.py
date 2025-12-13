import pytest
from bot.lib.mongodb import mongo_singleton


class _FastDummyMongoClient:
    """A very small fake MongoClient used in tests to avoid real network
    connections and long timeouts when code attempts to `MongoClient(url)`.

    This object implements __getitem__ to provide simple dict-like
    namespaces for tests and a close() method that is a no-op.
    """

    def __init__(self, url=None):
        self._url = url
        self.closed = False

    def __getitem__(self, name):
        # Provide a simple in-memory collection holder so tests that do
        # connection['logs'] or connection['something'] will not hit the network.
        if not hasattr(self, '_dbs'):
            self._dbs = {}
        if name not in self._dbs:
            self._dbs[name] = {}
        return self._dbs[name]

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def fast_mongo_client(monkeypatch):
    """Autouse fixture that patches the MongoClient in the singleton to a
    lightweight in-memory fake. This prevents tests from creating real
    PyMongo clients and waiting on network timeouts.

    Tests that need to exercise the original behavior can still monkeypatch
    the module-level `MongoClient` themselves inside the test.
    """
    # Reset any existing singleton instance to avoid cross-test contamination
    mongo_singleton.MongoClientSingleton._instance = None

    # Replace the MongoClient class used by the singleton with our fast fake
    monkeypatch.setattr(mongo_singleton, 'MongoClient', _FastDummyMongoClient)

    yield

    # Ensure we clear the singleton after each test
    mongo_singleton.MongoClientSingleton._instance = None
"""Shared pytest fixtures for all test modules.

This conftest.py provides session and module-scoped fixtures to reduce
test initialization overhead and improve overall test suite performance.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.tacobot import TacoBot

# ==============================================================================
# Autouse fixtures (automatically applied to all tests)
# ==============================================================================


@pytest.fixture(scope="session", autouse=True)
def mock_logs_database():
    """Mock LogsDatabase to prevent MongoDB connection attempts during tests.

    This fixture patches the LogsDatabase class at the logger module level
    so that when TacobotCog creates a Log instance, it doesn't try to connect to MongoDB.
    """
    with patch("bot.lib.logger.LogsDatabase") as mock_logs_db:
        mock_instance = MagicMock()
        mock_instance.insert_log = MagicMock()
        mock_logs_db.return_value = mock_instance
        yield mock_logs_db


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
    s.log_level = "INFO"  # Ensure this is a real string, not a mock
    s.settings_db = MagicMock()
    s.settings_db.set_setting = MagicMock()
    return s


# ==============================================================================
# Function-scoped fixtures (created once per test function - default)
# ==============================================================================


@pytest.fixture
def bot():
    """Function-scoped mock bot instance."""
    bot = MagicMock(spec=TacoBot)
    bot.user = MagicMock()
    bot.user.id = 999888777666555444
    bot.user.name = "TacoBot"
    bot.user.mention = "<@999888777666555444>"
    bot.fetch_guild = AsyncMock()
    bot.settings = MagicMock()
    bot.wait_for = AsyncMock()

    return bot

@pytest.fixture
def whitelist_manager():
    """Function-scoped mock whitelist manager."""
    wm = MagicMock()
    wm.get_minecraft_user = MagicMock()
    wm.get_whitelist_status = MagicMock()
    wm.get_minecraft_status = MagicMock()
    wm.is_user_whitelisted = MagicMock()
    wm.set_user_whitelist_status = MagicMock()
    return wm

@pytest.fixture
def metrics_db():
    """Function-scoped mock metrics database."""
    db = MagicMock()
    db.get_known_guilds = MagicMock(return_value=[])
    db.get_permission_counts = MagicMock(return_value=[])
    return db


@pytest.fixture
def pulltabs_db():
    """Function-scoped mock pulltabs database."""
    db = MagicMock()
    db.save_ticket = MagicMock()
    db.get_ticket = MagicMock(return_value={})
    db.is_ticket_redeemed = MagicMock(return_value=False)
    db.metric_pulltab_tickets_counts = MagicMock(return_value={})
    db.metric_pulltab_winnings = MagicMock(return_value={})
    db.metric_pulltab_winning_lines = MagicMock(return_value={})
    return db


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
    s.log_level = "INFO"  # Ensure this is a real string, not a mock
    s.settings_db = MagicMock()
    s.settings_db.set_setting = MagicMock()
    s.commands = {
        "foo": {
            "title": "Foo Command",
            "description": "Does foo things",
            "usage": "foo",
            "examples": ["foo bar"],
            "admin": False,
            "subcommands": {},
        }
    }
    s.changelog = "changelog.txt"
    s.prefixes = [".taco "]

    def settings_get(key, default=None):
        if key == "commands":
            return s.commands
        elif key == "prefixes":
            return s.prefixes
        elif key == "name":
            return s.name
        else:
            return default

    s.get = MagicMock(side_effect=settings_get)
    return s


@pytest.fixture
def permissions_db():
    """Function-scoped mock permissions database."""
    db = MagicMock()
    db.remove_user_permission = MagicMock()
    return db


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
def freegame_db():
    """Function-scoped mock FreeGameKeys database."""
    db = MagicMock()
    db.is_game_tracked = MagicMock(return_value=False)
    db.track_game = MagicMock()
    db.get_tracked_games = MagicMock(return_value=[])
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
def url_shortener():
    """Function-scoped UrlShortener instance with sane defaults for tests.

    Using this fixture avoids repeating the same constructor arguments in tests
    and makes it easy to swap test-wide defaults later if needed.
    """
    from bot.lib.UrlShortener import UrlShortener

    return UrlShortener(access_token="test-token", api_url="https://example.test")


@pytest.fixture
def mock_requests_post(monkeypatch):
    """Monkeypatch requests.post used by UrlShortener.shorten and return a MagicMock.

    Tests can modify the returned mock's .return_value to simulate various
    responses (text and json or side_effect on json()).
    """
    from unittest.mock import MagicMock

    m = MagicMock()
    monkeypatch.setattr("bot.lib.UrlShortener.requests.post", m)
    return m


@pytest.fixture
def entity_helper():
    """Function-scoped mock entity helper."""
    h = MagicMock()
    h.get_or_fetch_channel = AsyncMock()
    h.get_or_fetch_member = AsyncMock()
    h.get_or_fetch_user = AsyncMock()
    return h


@pytest.fixture
def identity_helper():
    """Function-scoped mock identity helper."""
    h = MagicMock()
    h.id = MagicMock(return_value="MockedID123")
    h.uuid = MagicMock(return_value="123e4567-e89b-12d3-a456-426614174000")
    return h


@pytest.fixture
def users_utils():
    """Function-scoped mock user utilities with async methods."""
    u = MagicMock()
    u.fetch_user_by_discord_id = AsyncMock()
    return u


@pytest.fixture
def taco_helper():
    """Function-scoped mock taco helper with async methods."""
    h = MagicMock()
    h.give_tacos = AsyncMock()
    h.get_taco_count = MagicMock(return_value=0)
    h.validate_user_can_spend = MagicMock(return_value=True)
    h.settings = MagicMock()
    return h


@pytest.fixture
def pulltab_helper(bot, identity_helper, pulltabs_db, settings):
    """Function-scoped real pulltab helper with mocked dependencies."""
    from bot.lib.helpers import PullTabHelper
    
    h = PullTabHelper(bot, identity_helper=identity_helper, pulltabs_db=pulltabs_db, settings=settings)
    return h


@pytest.fixture
def message_helper():
    """Function-scoped mock message helper with async methods."""
    h = MagicMock()
    h.notify_bot_not_initialized = AsyncMock()
    h.send_embed = AsyncMock()
    h.notify_of_error = AsyncMock()
    h.safe_delete_context_message = AsyncMock()
    return h


@pytest.fixture
def prompt_helper():
    """Function-scoped mock prompt helper with async methods."""
    h = MagicMock()
    h.ask_yes_no = AsyncMock()
    h.ask_text = AsyncMock()
    h.ask_number = AsyncMock()
    return h


@pytest.fixture
def context_helper():
    """Function-scoped mock context helper."""
    h = MagicMock()
    h.create_context = MagicMock()
    return h


@pytest.fixture
def birthdays_db():
    """Function-scoped mock birthdays database."""
    db = MagicMock()
    db.get_user_birthday = MagicMock(return_value=None)
    db.add_user_birthday = MagicMock()
    db.get_user_birthdays = MagicMock(return_value=[])
    db.birthday_was_checked_today = MagicMock(return_value=False)
    db.track_birthday_check = MagicMock()
    db.untrack_birthday_check = MagicMock()
    return db


@pytest.fixture
def shift_codes_db():
    """Function-scoped mock shift codes database."""
    db = MagicMock()
    return db


@pytest.fixture
def introductions_db():
    """Function-scoped mock introductions database."""
    db = MagicMock()
    db.get_user_introduction = MagicMock(return_value=None)
    db.get_user_introductions = MagicMock(return_value=[])
    return db


@pytest.fixture
def minecraft_db():
    """Function-scoped mock minecraft database."""
    db = MagicMock()
    db.get_minecraft_user = MagicMock()
    db.whitelist_minecraft_user = MagicMock()
    return db


@pytest.fixture
def metrics_config():
    """Create mock configuration object."""
    config = MagicMock()
    config.metrics = {"pollingInterval": 60}
    return config
