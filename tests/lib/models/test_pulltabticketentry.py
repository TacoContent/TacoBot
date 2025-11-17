import pytest

from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry


def test_from_dict_requires_ticket():
    data = {"guild_id": "1", "user_id": "2", "code": "X"}
    with pytest.raises(ValueError):
        PullTabTicketEntry.from_dict(data)


def test_from_dict_accepts_winning_indexes():
    data = {"guild_id": "1", "user_id": "2", "code": "X", "ticket": ["A"], "winning_line_indexes": [0, 1]}
    entry = PullTabTicketEntry.from_dict(data)
    assert entry.winning_line_indexes == [0, 1]
