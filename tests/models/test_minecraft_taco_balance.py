from bot.lib.models.MinecraftTacoBalance import MinecraftTacoBalance


def test_default_balance_is_empty():
    b = MinecraftTacoBalance()
    assert b.is_empty()
    assert b.to_dict() == {"balance": 0, "uuid": ""}


def test_balance_roundtrip():
    b = MinecraftTacoBalance(balance=25, uuid="uuid-9")
    assert not b.is_empty()
    d = b.to_dict()
    assert d["balance"] == 25
    assert d["uuid"] == "uuid-9"

    b2 = MinecraftTacoBalance.from_dict(d)
    assert isinstance(b2, MinecraftTacoBalance)
    assert b2.balance == 25
    assert b2.uuid == "uuid-9"
