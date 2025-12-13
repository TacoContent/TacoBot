import pytest
from bot.lib.models.ShiftCodePayload import ShiftCodeGame, ShiftCodePayload


def test_shift_code_payload_and_game():
    valid = {"games": [{"id": "g1", "name": "Game"}], "code": "abc", "created_at": 0}
    s = ShiftCodePayload(valid)
    d = s.to_dict()
    assert d["code"] == "abc" and isinstance(d["games"], list)

    # missing games
    with pytest.raises(ValueError):
        ShiftCodePayload({"games": [], "code": "x"})

    # missing code
    with pytest.raises(ValueError):
        ShiftCodePayload({"games": [{"id": "g1", "name": "Game"}], "code": ""})


def test_shift_code_payload_with_explicit_created_at():
    valid = {"games": [{"id": "g1", "name": "Game"}], "code": "abc", "created_at": 12345}
    s = ShiftCodePayload(valid)
    assert s.created_at == 12345
