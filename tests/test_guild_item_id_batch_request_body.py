import pytest
from bot.lib.models.GuildItemIdBatchRequestBody import GuildItemIdBatchRequestBody


class TestGuildItemIdBatchRequestBody:
    def test_init_with_ids_list(self):
        data = {"ids": [1, 2, "3", "foo"]}
        obj = GuildItemIdBatchRequestBody(data)
        # All ids should be coerced to str
        assert obj.ids == ["1", "2", "3", "foo"]

    def test_init_with_empty_ids(self):
        data = {"ids": []}
        obj = GuildItemIdBatchRequestBody(data)
        assert obj.ids == []

    def test_init_with_missing_ids(self):
        data = {"other": 123}
        obj = GuildItemIdBatchRequestBody(data)
        assert obj.ids == []

    def test_init_with_none_ids(self):
        data = {"ids": None}
        obj = GuildItemIdBatchRequestBody(data)
        # None should be treated as empty list
        assert obj.ids == []

    def test_to_dict(self):
        data = {"ids": ["a", "b", "c"]}
        obj = GuildItemIdBatchRequestBody(data)
        result = obj.to_dict()
        assert result == {"ids": ["a", "b", "c"]}

    def test_to_dict_after_modifying_ids(self):
        data = {"ids": [1, 2]}
        obj = GuildItemIdBatchRequestBody(data)
        obj.ids.append("extra")
        result = obj.to_dict()
        assert result == {"ids": ["1", "2", "extra"]}

    def test_init_with_ids_not_a_list(self):
        data = {"ids": "notalist"}
        obj = GuildItemIdBatchRequestBody(data)
        # Should treat as empty list
        assert obj.ids == []

    def test_init_with_ids_list_of_none(self):
        data = {"ids": [None, 5]}
        obj = GuildItemIdBatchRequestBody(data)
        # None coerced to 'None', 5 to '5'
        assert obj.ids == ["None", "5"]
