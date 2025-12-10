import pytest

from bot.lib.models.MinecraftUserStorageEntry import (
    MinecraftUserStorageEntry,
    MinecraftUserStorageItem,
)


def test_empty_entry_is_empty():
    e = MinecraftUserStorageEntry()
    assert e.is_empty()
    assert e.to_dict() == {
        "user_id": "",
        "guild_id": "",
        "uuid": "",
        "slots": 0,
        "storage": {},
    }


def test_entry_with_storage_items():
    payload = {
        "user_id": "123",
        "guild_id": "321",
        "uuid": "uuid-1",
        "username": "Steve",
        "storage": {
            "minecraft:diamond": {"item_id": "minecraft:diamond", "quantity": 64, "metadata": {"name": "Diamond"}},
            "minecraft:netherite_ingot": {"item_id": "minecraft:netherite_ingot", "quantity": 1, "metadata": {"name": "Netherite"}},
        },
    }

    entry = MinecraftUserStorageEntry(**payload)

    # not empty
    assert not entry.is_empty()

    # storage objects should be of the item class
    assert isinstance(entry.storage, dict)
    assert "minecraft:diamond" in entry.storage
    diamond = entry.storage["minecraft:diamond"]
    assert isinstance(diamond, MinecraftUserStorageItem)
    assert diamond.item_id == "minecraft:diamond"
    assert diamond.quantity == 64
    assert diamond.metadata == {"name": "Diamond"}


def test_from_dict_roundtrip():
    payload = {
        "user_id": "111",
        "guild_id": "222",
        "uuid": "a-uuid",
        "username": "Alex",
        "storage": {"allthemodium:allthemodium_ingot": {"item_id": "allthemodium:allthemodium_ingot", "quantity": 2, "metadata": {"name": "AllTheModium"}}},
    }

    entry = MinecraftUserStorageEntry.from_dict(payload)
    as_dict = entry.to_dict()

    # storage round trips as dicts with the same data
    assert as_dict["user_id"] == "111"
    assert as_dict["storage"]["allthemodium:allthemodium_ingot"]["quantity"] == 2
