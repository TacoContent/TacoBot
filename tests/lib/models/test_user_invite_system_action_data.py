from bot.lib.models.UserInviteSystemActionData import UserInviteSystemActionData


def test_to_dict_basic_fields():
    data = {
        "inviter_id": "123",
        "inviter_name": "Alice",
        "invited_id": "456",
        "invited_name": "Bob",
        "invite_code": "XYZ123",
    }
    obj = UserInviteSystemActionData(data)
    result = obj.to_dict()
    assert result == data


def test_to_dict_excludes_none():
    data = {"inviter_id": "123", "inviter_name": None, "invited_id": "456", "invited_name": "Bob", "invite_code": None}
    obj = UserInviteSystemActionData(data)
    result = obj.to_dict()
    # None values should be excluded
    assert "inviter_name" not in result
    assert "invite_code" not in result
    assert result["inviter_id"] == "123"
    assert result["invited_id"] == "456"
    assert result["invited_name"] == "Bob"


def test_to_dict_nested_to_dict():
    class Dummy:
        def to_dict(self):
            return {"foo": "bar"}

    data = {
        "inviter_id": Dummy(),
        "inviter_name": "Alice",
        "invited_id": "456",
        "invited_name": "Bob",
        "invite_code": "XYZ123",
    }
    obj = UserInviteSystemActionData(data)
    result = obj.to_dict()
    assert result["inviter_id"] == {"foo": "bar"}
    assert result["inviter_name"] == "Alice"
    assert result["invited_id"] == "456"
    assert result["invited_name"] == "Bob"
    assert result["invite_code"] == "XYZ123"


def test_defaults_when_missing():
    obj = UserInviteSystemActionData({})
    result = obj.to_dict()
    # All fields default to empty string
    assert result["inviter_id"] == ""
    assert result["inviter_name"] == ""
    assert result["invited_id"] == ""
    assert result["invited_name"] == ""
    assert result["invite_code"] == ""
