from bot.lib.models.PullTabRedeemedTicket import PullTabRedeemedTicket


def test_pulltab_redeemed_ticket_from_dict():
    data = {"success": True, "reward": 5, "message": "ok", "ticket": {"guild_id": 1, "user_id": 2, "code": "c", "ticket": ["a"]}}
    rt = PullTabRedeemedTicket.from_dict(data)
    assert rt.success and rt.ticket is not None


def test_pulltab_redeemed_ticket_to_dict_ticket_none():
    t = PullTabRedeemedTicket(success=False, reward=0, message="no", ticket=None)
    d = t.to_dict()
    assert d["ticket"] is None


def test_pulltab_redeemed_ticket_to_dict_with_ticket_object():
    from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry

    ticket = PullTabTicketEntry(guild_id=1, user_id=2, code="abc", ticket=["a"])
    t = PullTabRedeemedTicket(success=True, reward=10, message="ok", ticket=ticket)
    d = t.to_dict()
    assert d["ticket"]["code"] == "abc"
