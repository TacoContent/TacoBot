from unittest.mock import MagicMock

import discord
import pytest
from bot.cogs.tacos import TacosCog


@pytest.fixture
def cog(bot, settings, tacos_db, tracking_db, messaging, permissions, entity_helper, taco_helper):
    """Create TacosCog with injected dependencies from conftest.py."""
    c = TacosCog(
        bot=bot,
        settings=settings,
        tacos_db=tacos_db,
        tracking_db=tracking_db,
        messaging=messaging,
        permissions=permissions,
        entity_helper=entity_helper,
        taco_helper=taco_helper,
    )
    c.log = MagicMock()
    return c


@pytest.mark.asyncio
async def test_process_taco_gift(cog):
    cog.tacos_db.add_taco_gift = MagicMock()
    from unittest.mock import AsyncMock

    cog.taco_helper.give_tacos = AsyncMock()
    guild_id = 123
    giver = MagicMock(spec=discord.User)
    receiver = MagicMock(spec=discord.User)
    giver.id = 1
    receiver.id = 2
    type = MagicMock()
    amount = 5
    reason = "for being awesome"
    await cog._process_taco_gift(guild_id, giver, receiver, type, amount, reason)
    cog.tacos_db.add_taco_gift.assert_called_once_with(guild_id, giver.id, amount)
    cog.taco_helper.give_tacos.assert_awaited_once_with(guild_id, giver, receiver, reason, type, taco_amount=amount)


def test_track_tacos_command(cog):
    cog.tracking_db.track_command_usage = MagicMock()
    guild_id = 123
    channel_id = 456
    user_id = 789
    subcommand = "gift"
    args = [{"type": "command"}, {"user_id": 2}, {"amount": 5}, {"reason": "for being awesome"}]
    cog._track_tacos_command(guild_id, channel_id, user_id, subcommand, args)
    cog.tracking_db.track_command_usage.assert_called_once_with(
        guildId=guild_id, channelId=channel_id, userId=user_id, command="tacos", subcommand=subcommand, args=args
    )


def test_format_gift_success_message(cog):
    guild_id = 123

    def get_string(gid, key, **kwargs):
        if key == "taco_singular":
            return "taco"
        if key == "taco_plural":
            return "tacos"
        if key == "taco_gift_success":
            return (
                f"{kwargs['user']} gave {kwargs['touser']} {kwargs['amount']} {kwargs['taco_word']}. "
                f"Reason: {kwargs['reason']}"
            )
        return key

    cog.settings.get_string = MagicMock(side_effect=get_string)
    # Test singular
    msg = cog._format_gift_success_message(guild_id, "@giver", "@receiver", 1, "for fun")
    assert msg == "@giver gave @receiver 1 taco. Reason: for fun"
    # Test plural
    msg = cog._format_gift_success_message(guild_id, "@giver", "@receiver", 3, "for fun")
    assert msg == "@giver gave @receiver 3 tacos. Reason: for fun"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "giver_id, recipient_id, amount, total_gifted, max_gift_tacos, max_gift_taco_timespan, expected",
    [
        # Self-gift
        (1, 1, 1, 0, 10, 86400, (False, "self_gift")),
        # Exceeded max gifts
        (1, 2, 1, 10, 10, 86400, (False, "maximum")),
        # Amount exceeds remaining
        (1, 2, 5, 6, 10, 86400, (False, "limit_exceeded")),
        # Amount is zero
        (1, 2, 0, 0, 10, 86400, (False, "limit_exceeded")),
        # Valid gift
        (1, 2, 2, 3, 10, 86400, (True, None)),
    ],
)
async def test_validate_gift_eligibility(
    cog, giver_id, recipient_id, amount, total_gifted, max_gift_tacos, max_gift_taco_timespan, expected
):
    guild_id = 123

    # Setup settings.get_string to return a unique string for each error type
    def get_string(gid, key, **kwargs):
        if key == "taco_self_gift_message":
            return "self_gift"
        if key == "taco_gift_maximum":
            return "maximum"
        if key == "taco_gift_limit_exceeded":
            return "limit_exceeded"
        if key == "taco_plural":
            return "tacos"
        if key == "taco_singular":
            return "taco"
        return key

    cog.settings.get_string.side_effect = get_string
    cog.tacos_db.get_total_gifted_tacos.return_value = total_gifted
    result = cog._validate_gift_eligibility(
        guild_id=guild_id,
        giver_id=giver_id,
        recipient_id=recipient_id,
        amount=amount,
        max_gift_tacos=max_gift_tacos,
        max_gift_taco_timespan=max_gift_taco_timespan,
    )
    assert result == expected
