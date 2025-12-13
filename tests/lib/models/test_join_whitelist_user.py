from bot.lib.models.JoinWhitelistUser import JoinWhitelistAddedBy, JoinWhitelistUser


def test_join_whitelist_user_and_added_by():
    j = JoinWhitelistUser({"_id": "dbid", "guild_id": "10", "user_id": "20", "added_by": "x", "timestamp": 5})
    out = j.to_dict()
    assert "_id" not in out and out["guild_id"] == "10"

    a = JoinWhitelistAddedBy({"added_by": "someone"})
    assert a.to_dict()["added_by"] == "someone"
