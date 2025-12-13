import datetime
import types
from unittest.mock import MagicMock

from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry
from bot.lib.mongodb.minecraft import MinecraftDatabase


def make_settings(discounts=None):
    return {
        "storage": {"initial_slots": 9, "increase_cost": 1000},
        "discounts": discounts or [],
    }


def test_user_with_discount():
    db = MinecraftDatabase()

    # stub the user
    db.get_minecraft_user = MagicMock(return_value=MinecraftUserEntry(guild_id=1, user_id="123456789", role_ids=[]))

    # settings contains a discount for user 123456789
    db.settings = types.SimpleNamespace(
        get_settings=MagicMock(return_value=make_settings(discounts=[{"user_id": 123456789, "roles": [], "discount": 0.1, "expires": None}]))
    )

    got = db.get_user_shop_discount(guild_id=1, user_id="123456789")
    assert abs(got - 0.1) < 1e-8


def test_user_without_discount():
    db = MinecraftDatabase()
    db.get_minecraft_user = MagicMock(return_value=MinecraftUserEntry(guild_id=1, user_id="2222", role_ids=[]))
    db.settings = types.SimpleNamespace(get_settings=MagicMock(return_value=make_settings(discounts=[])))

    got = db.get_user_shop_discount(guild_id=1, user_id="2222")
    assert got == 0.0


def test_expired_discount_is_ignored():
    db = MinecraftDatabase()
    db.get_minecraft_user = MagicMock(return_value=MinecraftUserEntry(guild_id=1, user_id="5", role_ids=[]))

    past = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=1)
    db.settings = types.SimpleNamespace(get_settings=MagicMock(return_value=make_settings(discounts=[{"user_id": "5", "roles": [], "discount": 0.5, "expires": past}])))

    got = db.get_user_shop_discount(guild_id=1, user_id="5")
    assert got == 0.0


def test_role_based_discount():
    db = MinecraftDatabase()
    # user has role 42
    db.get_minecraft_user = MagicMock(return_value=MinecraftUserEntry(guild_id=1, user_id="99", role_ids=[42]))

    db.settings = types.SimpleNamespace(
        get_settings=MagicMock(return_value=make_settings(discounts=[{"user_id": None, "roles": [42], "discount": 0.2, "expires": None}]))
    )

    got = db.get_user_shop_discount(guild_id=1, user_id="99")
    assert abs(got - 0.2) < 1e-8


def test_highest_discount_wins():
    db = MinecraftDatabase()
    db.get_minecraft_user = MagicMock(return_value=MinecraftUserEntry(guild_id=1, user_id="123", role_ids=[7]))

    discounts = [
        {"user_id": 123, "roles": [], "discount": 0.05, "expires": None},
        {"user_id": None, "roles": [7], "discount": 0.12, "expires": None},
        {"user_id": 999, "roles": [], "discount": 0.9, "expires": None},
    ]

    db.settings = types.SimpleNamespace(get_settings=MagicMock(return_value=make_settings(discounts=discounts)))

    got = db.get_user_shop_discount(guild_id=1, user_id="123")
    # user-specific 0.05 vs role-based 0.12 -> 0.12 should be returned
    assert abs(got - 0.12) < 1e-8


def test_settings_missing_returns_zero_and_logs():
    db = MinecraftDatabase()
    db.get_minecraft_user = MagicMock(return_value=MinecraftUserEntry(guild_id=1, user_id="123", role_ids=[]))
    db.settings = types.SimpleNamespace(get_settings=MagicMock(return_value=None))

    got = db.get_user_shop_discount(guild_id=1, user_id="123")
    assert got == 0.0


def test_user_with_string_user_id_in_settings():
    db = MinecraftDatabase()

    # stub the user
    db.get_minecraft_user = MagicMock(return_value=MinecraftUserEntry(guild_id=1, user_id="123456789", role_ids=[]))

    # settings contains a discount for user '123456789' as a string
    db.settings = types.SimpleNamespace(
        get_settings=MagicMock(return_value=make_settings(discounts=[{"user_id": "123456789", "roles": [], "discount": 0.1, "expires": None}]))
    )

    got = db.get_user_shop_discount(guild_id=1, user_id="123456789")
    assert abs(got - 0.1) < 1e-8


def test_no_user_returns_zero():
    db = MinecraftDatabase()
    db.get_minecraft_user = MagicMock(return_value=None)
    db.settings = types.SimpleNamespace(get_settings=MagicMock())

    got = db.get_user_shop_discount(guild_id=1, user_id="notfound")
    assert got == 0.0
