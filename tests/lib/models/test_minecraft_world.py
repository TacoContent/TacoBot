import pytest

from bot.lib.models.minecraft.world import MinecraftWorld


def test_minecraft_world_validations_and_str():
    with pytest.raises(ValueError):
        MinecraftWorld(0, "n", "id", True)

    mw = MinecraftWorld(1, "n", "id", True)
    assert str(mw).startswith("n (")


def test_minecraft_world_missing_name_or_id_or_active():
    with pytest.raises(ValueError):
        MinecraftWorld(1, "", "id", True)

    with pytest.raises(ValueError):
        MinecraftWorld(1, "n", "", True)

    with pytest.raises(ValueError):
        MinecraftWorld(1, "n", "id", None)

    # to_dict returns dictionary with keys
    mw2 = MinecraftWorld(2, "other", "wid", False)
    d = mw2.to_dict()
    assert d["name"] == "other" and d["active"] is False
