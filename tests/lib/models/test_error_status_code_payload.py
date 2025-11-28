import pytest

from bot.lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload


def test_error_status_payload():
    # if message but missing error -> copy message
    p = ErrorStatusCodePayload({"message": "m"})
    assert p.error == "m"

    p2 = ErrorStatusCodePayload({"error": "e"})
    assert p2.message == "e"

    with pytest.raises(ValueError):
        ErrorStatusCodePayload({})

    # to_dict excludes None
    p3 = ErrorStatusCodePayload({"message": "m", "code": 5})
    d = p3.to_dict()
    assert d["message"] == "m" and d["code"] == 5
