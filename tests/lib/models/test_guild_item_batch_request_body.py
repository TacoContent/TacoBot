from bot.lib.models.GuildItemIdBatchRequestBody import GuildItemIdBatchRequestBody, GuildItemNameBatchRequestBody


def test_guild_item_batch_request_body():
    g = GuildItemIdBatchRequestBody({"ids": [1, "2"]})
    assert g.ids == ["1", "2"]
    g2 = GuildItemIdBatchRequestBody(None)
    assert g2.ids == []

    n = GuildItemNameBatchRequestBody({"names": ["a", 2]})
    assert n.names == ["a", "2"]


def test_batch_request_body_with_non_list_inputs():
    g = GuildItemIdBatchRequestBody({"ids": "notalist"})
    assert g.ids == []
    n = GuildItemNameBatchRequestBody({"names": "also-not-list"})
    assert n.names == []

def test_guild_item_batch_to_dict():
    g = GuildItemIdBatchRequestBody({"ids": [1, 2]})
    assert g.to_dict() == {"ids": ["1", "2"]}


def test_guild_item_name_batch_none_and_to_dict():
    n = GuildItemNameBatchRequestBody(None)
    assert n.names == []
    assert n.to_dict() == {"names": []}
