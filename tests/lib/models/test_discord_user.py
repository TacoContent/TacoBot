import datetime
from unittest.mock import MagicMock

from bot.lib.models.DiscordUser import DiscordUser


def test_discord_user_from_dict_and_from_user_mock(monkeypatch):
    # dict path
    u = DiscordUser({"id": "1", "name": "n", "discriminator": "0001"})
    d = u.to_dict()
    assert d["id"] == "1"

    # mock User: make it an actual instance of the module's User/Member types
    import bot.lib.models.DiscordUser as du_mod

    class FakeUser:
        pass

    monkeypatch.setattr(du_mod, "User", FakeUser, raising=False)
    monkeypatch.setattr(du_mod, "Member", FakeUser, raising=False)

    user = FakeUser()
    user.id = 3
    user.guild = MagicMock()
    user.guild.id = 100
    user.accent_color = MagicMock(value=123)
    user.avatar = MagicMock(url="http://a")
    user.banner = None
    user.bot = False
    user.color = None
    # don't rely on datetime.timestamp across platforms in unit tests
    user.created_at = None
    user.default_avatar = MagicMock(url="http://d")
    user.discriminator = "abcd"
    user.display_avatar = None
    user.display_name = "display"
    user.global_name = "global"
    user.name = "nm"
    user.system = False
    # status not present

    du = DiscordUser.fromUser(user)
    assert du.id == "3"
    out = du.to_dict()
    assert out["id"] == "3"


def test_discord_user_from_user_with_timestamp_and_numeric_discriminator(monkeypatch):
    # ensure created_at and numeric discriminator branch
    import bot.lib.models.DiscordUser as du_mod

    class FakeUser:
        pass

    monkeypatch.setattr(du_mod, "User", FakeUser, raising=False)
    monkeypatch.setattr(du_mod, "Member", FakeUser, raising=False)

    user = FakeUser()
    user.id = 7
    user.guild = MagicMock()
    user.guild.id = 11
    user.accent_color = None
    user.avatar = None
    user.banner = None
    user.bot = False
    user.color = None
    # created_at not a datetime -> should become None
    user.created_at = 12345
    user.default_avatar = None
    user.discriminator = "0008"
    user.display_avatar = None
    user.display_name = "d"
    user.global_name = None
    user.name = "name"
    user.system = False

    du = DiscordUser.fromUser(user)
    # discriminator is parsed to int then stringified -> '8'
    assert du.id == "7" and du.discriminator == "8"


def test_discord_user_status_and_created_at_datetime(monkeypatch):
    from datetime import datetime, timezone

    import bot.lib.models.DiscordUser as du_mod

    class FakeUser:
        pass

    monkeypatch.setattr(du_mod, "User", FakeUser, raising=False)
    monkeypatch.setattr(du_mod, "Member", FakeUser, raising=False)

    user = FakeUser()
    user.id = 55
    user.guild = MagicMock()
    user.guild.id = 66
    user.accent_color = None
    user.avatar = None
    user.banner = MagicMock(url="http://banner")
    user.bot = False
    user.color = None
    user.created_at = datetime.now(timezone.utc)
    user.default_avatar = MagicMock(url="http://d")
    user.discriminator = "0010"
    user.display_avatar = None
    user.display_name = "display"
    user.global_name = "global"
    user.name = "na"
    user.system = False
    user.status = MagicMock(value="online")

    du = DiscordUser.fromUser(user)
    out = du.to_dict()
    assert out["banner"] == "http://banner"
    assert out["status"] == "online"


def test_discord_user_to_dict_converts_asset_objects(monkeypatch):
    # verify that objects with 'url' are converted to urls in to_dict
    from bot.lib.models.DiscordUser import DiscordUser

    class Asset:
        def __init__(self, url):
            self.url = url

    data = {
        "id": "9",
        "name": "u",
        "default_avatar": Asset("http://default"),
        "avatar": Asset("http://avatar"),
        "display_avatar": Asset("http://display"),
        "banner": Asset("http://banner2"),
    }

    du = DiscordUser(data)
    out = du.to_dict()
    # ensure asset fields resolved to their url strings
    assert out["default_avatar"] == "http://default"
    assert out["avatar"] == "http://avatar"
    assert out["display_avatar"] == "http://display"
    assert out["banner"] == "http://banner2"


def test_discord_user_fromUser_with_dict_input():
    from bot.lib.models.DiscordUser import DiscordUser

    data = {"id": "100", "name": "tester", "discriminator": "1234"}
    du = DiscordUser.fromUser(data)
    assert isinstance(du, DiscordUser)
