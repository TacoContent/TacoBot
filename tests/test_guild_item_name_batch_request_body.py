import pytest
from bot.lib.models.GuildItemIdBatchRequestBody import GuildItemNameBatchRequestBody


class TestGuildItemNameBatchRequestBody:
    def test_init_with_names_list(self):
        data = {"names": [1, 2, "3", "foo"]}
        obj = GuildItemNameBatchRequestBody(data)
        # All names should be coerced to str
        assert obj.names == ["1", "2", "3", "foo"]

    def test_init_with_empty_names(self):
        data = {"names": []}
        obj = GuildItemNameBatchRequestBody(data)
        assert obj.names == []

    def test_init_with_missing_names(self):
        data = {"other": 123}
        obj = GuildItemNameBatchRequestBody(data)
        assert obj.names == []

    def test_init_with_none_ids(self):
        data = {"names": None}
        obj = GuildItemNameBatchRequestBody(data)
        # None should be treated as empty list
        assert obj.names == []

    def test_to_dict(self):
        data = {"names": ["a", "b", "c"]}
        obj = GuildItemNameBatchRequestBody(data)
        result = obj.to_dict()
        assert result == {"names": ["a", "b", "c"]}

    def test_to_dict_after_modifying_names(self):
        data = {"names": [1, 2]}
        obj = GuildItemNameBatchRequestBody(data)
        obj.names.append("extra")
        result = obj.to_dict()
        assert result == {"names": ["1", "2", "extra"]}

    def test_init_with_names_not_a_list(self):
        data = {"names": "not a list"}
        obj = GuildItemNameBatchRequestBody(data)
        # Should treat as empty list
        assert obj.names == []

    def test_init_with_names_list_of_none(self):
        data = {"names": [None, 5]}
        obj = GuildItemNameBatchRequestBody(data)
        # None coerced to 'None', 5 to '5'
        assert obj.names == ["None", "5"]
