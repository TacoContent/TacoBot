import pytest

from bot.lib.models.MinecraftStorageItemPayload import MinecraftStorageItemPayload


def test_empty_payload_is_empty():
    p = MinecraftStorageItemPayload()
    assert p.is_empty()
    assert p.to_dict() == {"uuid": "", "item": "", "quantity": 0, "metadata": {}}


def test_payload_fields_and_from_dict():
    data = {"uuid": "u-1", "item": "minecraft:diamond", "quantity": 10, "metadata": {"name": "Diamond"}}
    p = MinecraftStorageItemPayload(**data)
    assert not p.is_empty()
    assert p.uuid == "u-1"
    assert p.item_id == "minecraft:diamond"
    assert p.quantity == 10
    assert p.metadata == {"name": "Diamond"}

    # round-trip via dict
    as_dict = p.to_dict()
    assert as_dict["uuid"] == "u-1"
    assert as_dict["item"] == "minecraft:diamond"
    assert as_dict["quantity"] == 10

    # from_dict constructor
    p2 = MinecraftStorageItemPayload.from_dict(as_dict)
    assert isinstance(p2, MinecraftStorageItemPayload)
    assert p2.item_id == "minecraft:diamond"
