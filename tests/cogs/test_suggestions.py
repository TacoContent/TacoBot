from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from bot.cogs.suggestions import SuggestionsCog
from bot.lib.models.suggestionstates import SuggestionStates


@pytest.fixture
def cog():
    """Create a SuggestionsCog instance with all required dependencies mocked."""
    bot = MagicMock()
    suggestions_db = MagicMock()
    tracking_db = MagicMock()
    messaging = MagicMock()
    permissions = MagicMock()
    entity_helper = MagicMock()
    prompt_helper = MagicMock()
    taco_helper = MagicMock()
    context_helper = MagicMock()
    message_helper = MagicMock()
    settings = MagicMock()
    settings.get_settings = MagicMock(return_value={})
    settings.get_string = MagicMock(return_value="Test string")
    settings.log_level = "INFO"
    
    cog = SuggestionsCog(
        bot=bot,
        suggestions_db=suggestions_db,
        tracking_db=tracking_db,
        messaging=messaging,
        permissions=permissions,
        entity_helper=entity_helper,
        prompt_helper=prompt_helper,
        taco_helper=taco_helper,
        context_helper=context_helper,
        message_helper=message_helper,
        settings=settings,
    )
    # Mock the logger to prevent actual logging during tests
    cog.log = MagicMock()
    cog.log.debug = MagicMock()
    cog.log.error = MagicMock()
    return cog


@pytest.fixture
def suggestion():
    return {'id': 'suggestion123', 'state': SuggestionStates().ACTIVE, 'author_id': '42'}


@pytest.fixture
def user():
    u = MagicMock(spec=discord.User)
    u.id = 42
    u.mention = '@user42'
    u.name = 'TestUser'
    return u


@pytest.fixture
def message():
    m = MagicMock(spec=discord.Message)
    m.embeds = [MagicMock()]
    return m


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "approve_count, reject_count, implemented_count, consider_count, expected_state",
    [
        (0, 1, 0, 0, SuggestionStates().REJECTED),
        (0, 0, 1, 0, SuggestionStates().IMPLEMENTED),
        (0, 0, 0, 1, SuggestionStates().CONSIDERED),
        (0, 0, 0, 0, SuggestionStates().ACTIVE),
    ],
)
async def test_handle_admin_approve_emoji_remove(
    cog, suggestion, user, message, approve_count, reject_count, implemented_count, consider_count, expected_state
):
    cog.suggestions_db.set_state_suggestion_by_id = MagicMock()
    cog.update_suggestion_state = AsyncMock()
    await cog._handle_admin_approve_emoji_remove(
        reject_count=reject_count,
        implemented_count=implemented_count,
        consider_count=consider_count,
        approve_count=approve_count,
        guild_id=123,
        suggestion=suggestion,
        user=user,
        message=message,
        author=user,
    )
    if approve_count <= 0:
        cog.suggestions_db.set_state_suggestion_by_id.assert_called_with(
            123, suggestion['id'], expected_state, user.id, 'Approve State Was Removed'
        )
        cog.update_suggestion_state.assert_awaited()
    else:
        cog.suggestions_db.set_state_suggestion_by_id.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "consider_count, reject_count, implemented_count, approve_count, expected_state",
    [
        (0, 1, 0, 0, SuggestionStates().REJECTED),
        (0, 0, 1, 0, SuggestionStates().IMPLEMENTED),
        (0, 0, 0, 1, SuggestionStates().APPROVED),
        (0, 0, 0, 0, SuggestionStates().ACTIVE),
    ],
)
async def test_handle_admin_consider_emoji_remove(
    cog, suggestion, user, message, consider_count, reject_count, implemented_count, approve_count, expected_state
):
    cog.suggestions_db.set_state_suggestion_by_id = MagicMock()
    cog.update_suggestion_state = AsyncMock()
    await cog._handle_admin_consider_emoji_remove(
        reject_count=reject_count,
        implemented_count=implemented_count,
        consider_count=consider_count,
        approve_count=approve_count,
        guild_id=123,
        suggestion=suggestion,
        user=user,
        message=message,
        author=user,
    )
    if consider_count <= 0:
        cog.suggestions_db.set_state_suggestion_by_id.assert_called_with(
            123, suggestion['id'], expected_state, user.id, 'Consider State Was Removed'
        )
        cog.update_suggestion_state.assert_awaited()
    else:
        cog.suggestions_db.set_state_suggestion_by_id.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "implemented_count, reject_count, consider_count, approve_count, expected_state",
    [
        (0, 1, 0, 0, SuggestionStates().REJECTED),
        (0, 0, 1, 0, SuggestionStates().CONSIDERED),
        (0, 0, 0, 1, SuggestionStates().APPROVED),
        (0, 0, 0, 0, SuggestionStates().ACTIVE),
    ],
)
async def test_handle_admin_implemented_emoji_remove(
    cog, suggestion, user, message, implemented_count, reject_count, consider_count, approve_count, expected_state
):
    cog.suggestions_db.set_state_suggestion_by_id = MagicMock()
    cog.update_suggestion_state = AsyncMock()
    await cog._handle_admin_implemented_emoji_remove(
        reject_count=reject_count,
        implemented_count=implemented_count,
        consider_count=consider_count,
        approve_count=approve_count,
        guild_id=123,
        suggestion=suggestion,
        user=user,
        message=message,
        author=user,
    )
    if implemented_count <= 0:
        cog.suggestions_db.set_state_suggestion_by_id.assert_called_with(
            123, suggestion['id'], expected_state, user.id, 'Implemented State Was Removed'
        )
        cog.update_suggestion_state.assert_awaited()
    else:
        cog.suggestions_db.set_state_suggestion_by_id.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reject_count, implemented_count, consider_count, approve_count, expected_state",
    [
        (0, 1, 0, 0, SuggestionStates().IMPLEMENTED),
        (0, 0, 1, 0, SuggestionStates().CONSIDERED),
        (0, 0, 0, 1, SuggestionStates().APPROVED),
        (0, 0, 0, 0, SuggestionStates().ACTIVE),
    ],
)
async def test_handle_admin_reject_emoji_remove(
    cog, suggestion, user, message, reject_count, implemented_count, consider_count, approve_count, expected_state
):
    cog.suggestions_db.set_state_suggestion_by_id = MagicMock()
    cog.update_suggestion_state = AsyncMock()
    await cog._handle_admin_reject_emoji_remove(
        reject_count=reject_count,
        implemented_count=implemented_count,
        consider_count=consider_count,
        approve_count=approve_count,
        guild_id=123,
        suggestion=suggestion,
        user=user,
        message=message,
        author=user,
    )
    if reject_count <= 0:
        cog.suggestions_db.set_state_suggestion_by_id.assert_called_with(
            123, suggestion['id'], expected_state, user.id, 'Reject State Was Removed'
        )
        cog.update_suggestion_state.assert_awaited()
    else:
        cog.suggestions_db.set_state_suggestion_by_id.assert_not_called()


def test_get_color_for_state(cog):
    states = SuggestionStates()
    assert cog.get_color_for_state(states.APPROVED) == 0x00FF00
    assert cog.get_color_for_state(states.CONSIDERED) == 0xFFFF00
    assert cog.get_color_for_state(states.IMPLEMENTED) == 0xAAAAAA
    assert cog.get_color_for_state(states.REJECTED) == 0xFF0000
    assert cog.get_color_for_state(states.ACTIVE) == 0x7289DA
    assert cog.get_color_for_state(states.CLOSED) is None
