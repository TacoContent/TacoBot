import datetime
from unittest.mock import MagicMock

import pytest

from bot.lib.models.DiscordMessage import DiscordMessage


def test_discord_message_from_dict_and_to_dict():
    data = {"id": "1", "channel_id": "2", "content": "hello"}
    dm = DiscordMessage(data)
    assert dm.to_dict()["content"] == "hello"


def test_discord_message_from_message_mock(monkeypatch):
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    # create a fake Message class inside the module so isinstance checks pass
    import bot.lib.models.DiscordMessage as dm_mod

    class FakeMessage(MagicMock):
        pass

    monkeypatch.setattr(dm_mod, "discord", dm_mod.discord)
    # replace Message class inside discord module namespace used by the module
    monkeypatch.setattr(dm_mod.discord, "Message", FakeMessage, raising=False)

    msg = FakeMessage()
    msg.id = 123
    msg.channel = MagicMock()
    msg.channel.id = 456
    msg.guild = MagicMock()
    msg.guild.id = 10
    msg.author = MagicMock()
    msg.author.id = 99
    msg.content = "x"
    msg.created_at = now
    msg.jump_url = "http://jump"
    msg.edited_at = None
    mention = MagicMock()
    mention.id = 5
    mention.name = "u"
    msg.mentions = [mention]
    attachment = MagicMock()
    attachment.id = 2
    attachment.url = "http://a"
    msg.attachments = [attachment]
    embed = MagicMock()
    embed.to_dict.return_value = {"embed": True}
    msg.embeds = [embed]
    # reactions resolved via DiscordMessageReaction.from_message
    reaction = MagicMock()
    reaction.emoji = "🙂"
    reaction.count = 3
    msg.reactions = [reaction]
    msg.nonce = None
    msg.pinned = False
    msg.type = 0

    dm = DiscordMessage.fromMessage(msg)
    out = dm.to_dict()
    assert out["id"] == "123"
    assert isinstance(out["reactions"], list)


def test_discord_message_from_message_with_edited_and_no_guild(monkeypatch):
    # test branch where message.guild is None and edited_at present
    import bot.lib.models.DiscordMessage as dm_mod

    class FakeMessage(MagicMock):
        pass

    monkeypatch.setattr(dm_mod.discord, "Message", FakeMessage, raising=False)

    msg = FakeMessage()
    msg.id = 12
    msg.channel = MagicMock()
    msg.channel.id = 13
    msg.guild = None
    msg.author = MagicMock()
    msg.author.id = 14
    msg.content = "c"
    msg.created_at = MagicMock()
    msg.created_at.timestamp.return_value = 2
    msg.jump_url = None
    msg.edited_at = MagicMock()
    msg.edited_at.timestamp.return_value = 3
    msg.mentions = []
    msg.attachments = []
    msg.embeds = []
    msg.reactions = []
    msg.nonce = None
    msg.pinned = True
    msg.type = 1

    dm = DiscordMessage.fromMessage(msg)
    assert dm.guild_id == "0" and dm.edited_at == 3


def test_discord_fromMessage_with_dict():
    data = {"id": "2", "channel_id": "3", "content": "dict-path"}
    dm = DiscordMessage.fromMessage(data)
    assert dm.content == "dict-path"


def test_discord_message_invalid_fromMessage_raises():
    with pytest.raises(ValueError):
        DiscordMessage.fromMessage(123)
