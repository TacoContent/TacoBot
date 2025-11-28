from bot.lib.models.PagedResults import PagedResults, PagedResultsJoinWhitelistUser


def test_paged_results():
    pr = PagedResults({"total": 10, "skip": 2, "take": 5, "items": [1, 2]})
    assert pr.to_dict()["total"] == 10
    pr2 = PagedResultsJoinWhitelistUser({"items": []})
    assert isinstance(pr2.items, list)
