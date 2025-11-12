from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.cogs.voicechat import VoiceChatCog


@pytest.fixture
def cog(bot, entity_helper, taco_helper, settings):
    # Patch taco_helper.give_tacos to be async
    taco_helper.give_tacos = AsyncMock()
    # Patch settings.get_string to return a dummy reason
    settings.get_string = MagicMock(return_value="Created voice channel!")
    # Patch get_cog_settings to return a config with allowed channel
    vc_cog = VoiceChatCog(bot=bot, entity_helper=entity_helper, tacos_helper=taco_helper, settings=settings)
    vc_cog.get_cog_settings = MagicMock(return_value={"channels": ["123"]})
    return vc_cog


class DummyGuild:
    def __init__(self, id):
        self.id = id


class DummyChannel:
    def __init__(self, id):
        self.id = id


class DummyMember:
    def __init__(self, name, guild=None, bot=False, system=False):
        self.name = name
        self.guild = guild
        self.bot = bot
        self.system = system


@pytest.mark.asyncio
async def test_on_voice_state_update_no_guild(cog):
    member = DummyMember(name="User", guild=None)
    before = MagicMock(channel=None)
    after = MagicMock(channel=None)
    await cog.on_voice_state_update(member, before, after)
    cog.tacos_helper.give_tacos.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_voice_state_update_bot_or_system(cog):
    guild = DummyGuild(id=1)
    member_bot = DummyMember(name="Bot", guild=guild, bot=True)
    member_system = DummyMember(name="System", guild=guild, system=True)
    before = MagicMock(channel=None)
    after = MagicMock(channel=None)
    await cog.on_voice_state_update(member_bot, before, after)
    await cog.on_voice_state_update(member_system, before, after)
    cog.tacos_helper.give_tacos.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_voice_state_update_user_leaves_channel(cog):
    guild = DummyGuild(id=2)
    member = DummyMember(name="User", guild=guild)
    before = MagicMock(channel=DummyChannel(id=123))
    after = MagicMock(channel=None)
    await cog.on_voice_state_update(member, before, after)
    cog.tacos_helper.give_tacos.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_voice_state_update_user_joins_untracked_channel(cog):
    guild = DummyGuild(id=3)
    member = DummyMember(name="User", guild=guild)
    before = MagicMock(channel=None)
    after = MagicMock(channel=DummyChannel(id=999))
    # Patch get_cog_settings to not include channel 999
    cog.get_cog_settings.return_value = {"channels": ["123"]}
    await cog.on_voice_state_update(member, before, after)
    cog.tacos_helper.give_tacos.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_voice_state_update_user_joins_tracked_channel(cog):
    guild = DummyGuild(id=4)
    member = DummyMember(name="User", guild=guild)
    before = MagicMock(channel=None)
    after = MagicMock(channel=DummyChannel(id=123))
    cog.get_cog_settings.return_value = {"channels": ["123"]}
    await cog.on_voice_state_update(member, before, after)
    from bot.lib.enums.tacotypes import TacoTypes

    cog.tacos_helper.give_tacos.assert_awaited_once_with(
        guildId=4,
        fromUser=cog.bot.user,
        toUser=member,
        reason="Created voice channel!",
        give_type=TacoTypes.CREATE_VOICE_CHANNEL,
        taco_amount=0,
    )


@pytest.mark.asyncio
async def test_on_voice_state_update_exception(monkeypatch, cog):
    guild = DummyGuild(id=5)
    member = DummyMember(name="User", guild=guild)
    before = MagicMock(channel=None)
    after = MagicMock(channel=DummyChannel(id=123))
    cog.get_cog_settings.side_effect = Exception("fail")
    error_called = {}

    def fake_error(guild_id, module, msg, tb):
        error_called['called'] = True
        error_called['guild_id'] = guild_id
        error_called['msg'] = msg

    monkeypatch.setattr(cog.log, "error", fake_error)
    await cog.on_voice_state_update(member, before, after)
    assert error_called['called']
    assert "fail" in error_called['msg']


@pytest.mark.asyncio
async def test_setup(monkeypatch, bot, entity_helper, taco_helper, settings):
    monkeypatch.setattr("bot.cogs.voicechat.Settings", lambda: settings)
    monkeypatch.setattr("bot.cogs.voicechat.EntityHelper", lambda b: entity_helper)
    monkeypatch.setattr("bot.cogs.voicechat.TacoHelper", lambda b, entity_helper=None: taco_helper)
    add_cog_called = {}

    async def fake_add_cog(cog_instance):
        add_cog_called['called'] = True
        add_cog_called['cog'] = cog_instance

    bot.add_cog = AsyncMock(side_effect=fake_add_cog)
    from bot.cogs.voicechat import setup

    await setup(bot)
    assert add_cog_called['called']
    assert isinstance(add_cog_called['cog'], VoiceChatCog)
