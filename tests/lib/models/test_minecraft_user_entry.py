from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry, MinecraftUserOpData


def test_minecraft_user_entry_and_opdata():
    m = MinecraftUserEntry(guild_id=1, user_id=2, username="u", uuid="uuid", whitelist=True, op={"enabled": True, "level": 4, "bypassesPlayerLimit": True})
    d = m.to_dict()
    assert d["guild_id"] == "1" and "op" in d

    # from_dict without op
    m2 = MinecraftUserEntry.from_dict({"guild_id": "5", "user_id": "6", "username": "x", "uuid": "u"})
    assert isinstance(m2, MinecraftUserEntry)

    op = MinecraftUserOpData(enabled=True, level=2, bypassesPlayerLimit=False)
    assert op.to_dict()["level"] == 2
    op2 = MinecraftUserOpData.from_dict({"enabled": False, "level": 1, "bypassesPlayerLimit": True})
    assert isinstance(op2, MinecraftUserOpData)


def test_minecraft_user_entry_from_dict_with_op_partial():
    # include op with missing keys to check defaults
    data = {"guild_id": "2", "user_id": "3", "username": "u", "uuid": "uu", "op": {"enabled": True}}
    m = MinecraftUserEntry.from_dict(data)
    assert isinstance(m, MinecraftUserEntry)
    assert "op" in m.to_dict()


def test_minecraft_user_entry_to_dict_without_op():
    m2 = MinecraftUserEntry.from_dict({"guild_id": "15", "user_id": "16", "username": "u", "uuid": "uu"})
    d = m2.to_dict()
    assert "op" not in d
