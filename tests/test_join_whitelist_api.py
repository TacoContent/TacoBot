"""Unit tests for JoinWhitelistApiHandler internal pagination logic.

These tests focus on the pure helper `_paginate` to avoid depending on
the full HTTP framework or a live database. Additional integration
tests could be added once a test harness for the HTTP layer is in place.
"""

from bot.lib.http.handlers.api.v1.JoinWhitelistApiHandler import JoinWhitelistApiHandler


def test_paginate_basic():
    items = [{"i": i} for i in range(10)]
    result = JoinWhitelistApiHandler._paginate(items, 0, 5)
    assert len(result) == 5
    assert result[0]["i"] == 0
    assert result[-1]["i"] == 4


def test_paginate_skip():
    items = [{"i": i} for i in range(10)]
    result = JoinWhitelistApiHandler._paginate(items, 5, 3)
    assert len(result) == 3
    assert result[0]["i"] == 5
    assert result[-1]["i"] == 7


def test_paginate_skip_past_end():
    items = [{"i": i} for i in range(5)]
    result = JoinWhitelistApiHandler._paginate(items, 10, 5)
    assert result == []


def test_paginate_negative_inputs():
    items = [{"i": i} for i in range(5)]
    # negative skip coerced to 0; negative take coerced to 0 -> returns []
    result = JoinWhitelistApiHandler._paginate(items, -5, -10)
    assert result == []
