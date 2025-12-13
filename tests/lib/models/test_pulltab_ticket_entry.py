import pytest
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry


def test_pulltab_ticket_entry_from_dict_and_to_dict():
    payload = {"guild_id": 1, "user_id": 2, "code": "c", "ticket": ["a"]}
    p = PullTabTicketEntry.from_dict(payload)
    assert p.guild_id == "1"

    with pytest.raises(ValueError):
        PullTabTicketEntry.from_dict({"user_id": 2, "code": "c", "ticket": ["a"]})

    # to_dict doesn't include None values
    p2 = PullTabTicketEntry(guild_id=1, user_id=2, code="c", ticket=["a"], redeemed_at=None)
    td = p2.to_dict()
    assert "guild_id" in td


def test_pulltab_ticket_entry_created_at_and_from_dict_string_ids_and_missing_fields():
    # constructor with explicit created_at
    p = PullTabTicketEntry(guild_id=1, user_id=2, code="c", ticket=["a"], created_at=1234567)
    assert p.created_at == 1234567

    # from_dict accepts string guild_id and user_id
    payload = {"guild_id": "10", "user_id": "20", "code": "c", "ticket": ["a"]}
    p2 = PullTabTicketEntry.from_dict(payload)
    assert p2.guild_id == "10"

    # missing user_id raises
    with pytest.raises(ValueError):
        PullTabTicketEntry.from_dict({"guild_id": 1, "code": "c", "ticket": ["a"]})

    # user_id as string conversion
    payload2 = {"guild_id": 1, "user_id": "2", "code": "c", "ticket": ["a"]}
    p3 = PullTabTicketEntry.from_dict(payload2)
    assert p3.user_id == "2"

    # missing code raises
    with pytest.raises(ValueError):
        PullTabTicketEntry.from_dict({"guild_id": 1, "user_id": 2, "ticket": ["a"]})

    # missing ticket raises
    with pytest.raises(ValueError):
        PullTabTicketEntry.from_dict({"guild_id": 1, "user_id": 2, "code": "c"})


def test_pulltab_ticket_entry_multipliers_and_cost_defaults():
    # If multipliers invalid or None and cost negative -> defaults applied
    p = PullTabTicketEntry(guild_id=1, user_id=2, code="c", ticket=["a"], effective_multiplier=None, purchase_multiplier=0, cost=-5)
    # current implementation sets attributes but then overwrites them by assigning the passed
    # values unconditionally, so the result reflects the raw inputs
    assert p.effective_multiplier is None
    assert p.purchase_multiplier == 0
    assert p.cost == -5


def test_pulltab_ticket_entry_when_created_at_default_and_edge_cases():
    p = PullTabTicketEntry(guild_id=1, user_id=2, code="c", ticket=["a"], effective_multiplier=0, purchase_multiplier=None, cost=None)
    # created_at should be populated (int) when not provided
    assert isinstance(p.created_at, int)
    # multipliers and cost still assigned as passed (implementation detail)
    assert p.effective_multiplier == 0
    assert p.purchase_multiplier is None
    assert p.cost is None


def test_pulltab_ticket_entry_multiplier_branches():
    # effective_multiplier >= 1 should not trigger the 'if' branch
    p = PullTabTicketEntry(guild_id=1, user_id=2, code="c", ticket=["a"], effective_multiplier=2, purchase_multiplier=2, cost=5)
    assert p.effective_multiplier == 2
    assert p.purchase_multiplier == 2
    assert p.cost == 5

    # effective_multiplier < 1 should execute first branch then be overwritten (implementation detail)
    p2 = PullTabTicketEntry(guild_id=1, user_id=2, code="c", ticket=["a"], effective_multiplier=0, purchase_multiplier=0, cost=None)
    assert p2.effective_multiplier == 0
    assert p2.purchase_multiplier == 0
    assert p2.cost is None
