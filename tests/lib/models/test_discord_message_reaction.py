from unittest.mock import MagicMock

import pytest
from bot.lib.models.DiscordMessageReaction import DiscordMessageReaction


def test_discord_reaction_to_and_from():
    r = DiscordMessageReaction("🙂", 4)
    assert r.to_dict()["count"] == 4

    msg = MagicMock()
    r2 = MagicMock()
    r2.emoji = "x"
    r2.count = 1
    msg.reactions = [r2]
    got = DiscordMessageReaction.from_message(msg)
    assert isinstance(got, list) and got[0].emoji == "x"

    # dict conversion
    dr = DiscordMessageReaction.from_message_reaction({"emoji": "a", "count": 2})
    assert dr.emoji == "a"

    with pytest.raises(ValueError):
        DiscordMessageReaction.from_message_reaction({"emoji": 5, "count": "no"})

    with pytest.raises(ValueError):
        DiscordMessageReaction.from_message_reaction(object())


def test_reaction_from_real_reaction(monkeypatch):
    # patch the discord.Reaction class in the module so isinstance checks work
    import bot.lib.models.DiscordMessageReaction as r_mod

    class FakeReaction:
        def __init__(self, emoji, count):
            self.emoji = emoji
            self.count = count

    monkeypatch.setattr(r_mod, "discord", r_mod.discord)
    monkeypatch.setattr(r_mod.discord, "Reaction", FakeReaction, raising=False)

    fr = FakeReaction("X", 9)
    res = r_mod.DiscordMessageReaction.from_message_reaction(fr)
    assert res.emoji == "X" and res.count == 9


def test_reaction_from_dict_missing_keys_raises():
    from bot.lib.models.DiscordMessageReaction import DiscordMessageReaction

    with pytest.raises(ValueError):
        DiscordMessageReaction.from_message_reaction({"emoji": "a"})
