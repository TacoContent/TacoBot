import pytest
from bot.cogs.pulltab import PullTabCog
from unittest.mock import MagicMock, AsyncMock
from discord import Interaction
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry


@pytest.fixture
def cog(bot, settings, message_helper, permissions, identity_helper, pulltabs_db, taco_helper, entity_helper):
    return PullTabCog(
        bot=bot,
        settings=settings,
        message_helper=message_helper,
        permissions=permissions,
        identity_helper=identity_helper,
        taco_helper=taco_helper,
        entity_helper=entity_helper,
        pulltabs_db=pulltabs_db,
    )


def make_probabilities():
    return [
        {
            "symbol": "🌮",
            "weight": 50,
            "rules": [
                {"match": "🌮", "reward": 100},
                {"match": "🌮🌮", "reward": 1000},
                {"match": "🌮🌮🌮", "reward": 10000},
            ],
        },
        {"symbol": "🍉", "weight": 20, "rules": [{"match": "🍉🍉🍉", "reward": 500}]},
        {"symbol": "🍎", "weight": 30, "rules": [{"match": "🍎🍎", "reward": 2000}]},
    ]


def test_exact_full_line_match(cog):
    probs = make_probabilities()
    ticket = ["🌮🌮🌮"]
    is_winner, reward, lines, indexes, effective_multiplier = cog._process_ticket(ticket, {"probabilities": probs}, effective_multiplier=1.0)
    assert is_winner
    assert reward == 10000
    assert any("🌮🌮🌮" in x for x in lines)
    assert indexes == [0]


def test_two_tacos_any_order_match(cog):
    probs = make_probabilities()
    ticket = ["🌮🍎🌮"]
    is_winner, reward, lines, indexes, effective_multiplier = cog._process_ticket(ticket, {"probabilities": probs}, effective_multiplier=1.0)
    assert is_winner
    assert reward == 1000
    assert any("🌮🌮" in x for x in lines)
    assert indexes == [0]


def test_no_two_tacos(cog):
    probs = make_probabilities()
    ticket = ["🌮🍎🍉"]
    is_winner, reward, lines, indexes, effective_multiplier = cog._process_ticket(ticket, {"probabilities": probs}, effective_multiplier=1.0)
    # single taco should award the single-symbol reward
    assert is_winner
    assert reward == 100
    assert any("🌮" in x for x in lines)
    assert indexes == [0]


def test_multiple_rule_matches(cog):
    # Two tacos -> should match the highest rule for the symbol (two-taco rule)
    probs = make_probabilities()
    # add small reward for single taco to ensure both are counted
    ticket = ["🌮🌮🍎"]
    is_winner, reward, lines, indexes, effective_multiplier = cog._process_ticket(ticket, {"probabilities": probs}, effective_multiplier=1.0)
    # should win for the double-taco rule only (avoid double-counting)
    assert is_winner
    assert any("🌮🌮" in x for x in lines)
    assert reward == 1000
    # Ensure a single-taco line was not separately awarded; avoid substring matches
    assert not any(x.strip() == "🌮 -> 100" for x in lines)
    assert indexes == [0]


def test_multiline_ticket_with_skull_blocks(cog):
    # Build probabilities with skull rule that denies payouts
    probs = [
        {"symbol": "🌮", "weight": 50, "rules": [{"match": "🌮", "reward": 100}]},
        {"symbol": "🍊", "weight": 30, "rules": []},
        {"symbol": "💀", "weight": 1, "rules": [{"match": "💀", "reward": 0, "multiplier": 0}]},
        {"symbol": "🍊", "weight": 10, "rules": [{"match": "🍊🍊", "reward": 50}]},
    ]

    ticket = [
        "💀🍊🍊",
        "🍊🍒🍇",
        "🍎🌮🍒",
        "🍉🍇💀",
        "🍊🌮🍇",
    ]

    is_winner, reward, lines, indexes, effective_multiplier = cog._process_ticket(ticket, {"probabilities": probs}, effective_multiplier=1.0)
    assert is_winner
    # Lines 3 and 5 have single taco each (100 + 100)
    assert reward == 200
    assert len(lines) == 2
    # Should mark rows 3 and 5 (0-based indices 2 and 4)
    assert set(indexes) == {2, 4}


def test_complex_multiline_awards_with_skull(cog):
    probs = [
        {"symbol": "🌮", "weight": 50, "rules": [{"match": "🌮", "reward": 100}, {"match": "🌮🌮", "reward": 1000}]},
        {"symbol": "💀", "weight": 1, "rules": [{"match": "💀", "reward": 0, "multiplier": 0}]},
    ]

    ticket = [
        "🌮🌮🍉",  # 1000
        "🌮🍉🌮",  # 1000
        "🌮🌮💀",  # 0 because skull present
        "🍎🍀🍊",  # 0 (no rule for combo)
        "🍀🍀🌮",  # 100 (single taco = 100)  <-- Example had 100
    ]

    is_winner, reward, lines, indexes, effective_multiplier = cog._process_ticket(ticket, {"probabilities": probs}, effective_multiplier=1.0)
    assert is_winner
    assert reward == 2100
    assert set(indexes) == {0, 1, 4}


def test_real_probabilities_triple_matches_and_skull_block(cog):
    # Use the user's real probabilities configuration
    probs = [
        {
            "symbol": "🌮",
            "weight": 0.2,
            "rules": [
                {"match": "🌮", "reward": 100},
                {"match": "🌮🌮", "reward": 1000},
                {"match": "🌮🌮🌮", "reward": 10000},
            ],
        },
        {"symbol": "🍀", "weight": 0.75, "rules": [{"match": "🍀🍀🍀", "reward": 5000}]},
        {"symbol": "🍎", "weight": 0.9, "rules": [{"match": "🍎🍎🍎", "reward": 500}]},
        {"symbol": "🍊", "weight": 0.9, "rules": [{"match": "🍊🍊🍊", "reward": 250}]},
        {"symbol": "🍉", "weight": 1, "rules": [{"match": "🍉🍉🍉", "reward": 200}]},
        {"symbol": "🍇", "weight": 1, "rules": [{"match": "🍇🍇🍇", "reward": 150}]},
        {"symbol": "🍒", "weight": 1, "rules": [{"match": "🍒🍒🍒", "reward": 100}]},
        {"symbol": "💀", "weight": 0.5, "rules": [{"match": "💀", "reward": -99999999, "multiplier": 0}]},
    ]

    # Single line triple clover
    ticket = ["🍀🍀🍀"]
    is_winner, reward, lines, indexes, effective_multiplier = cog._process_ticket(
        ticket, {"probabilities": probs}, effective_multiplier=1.0
    )
    assert is_winner
    assert reward == 5000

    # Skull blocks a line even when clover is present
    ticket = ["🍀💀🍀"]
    is_winner, reward, lines, indexes, effective_multiplier = cog._process_ticket(
        ticket, {"probabilities": probs}, effective_multiplier=1.0
    )
    assert not is_winner or reward == 0
    assert indexes == []

    # Triple taco should be recognized
    ticket = ["🌮🌮🌮"]
    is_winner, reward, lines, indexes, effective_multiplier = cog._process_ticket(
        ticket, {"probabilities": probs}, effective_multiplier=1.0
    )
    assert is_winner
    assert reward == 10000
    assert indexes == [0]


def test_generate_ticket_adds_code_and_returns_output(cog, monkeypatch):
    # Build simple probabilities and a small ticket grid for deterministic output
    probs = [{"symbol": "🌮", "weight": 1, "rules": []}, {"symbol": "🍎", "weight": 1, "rules": []}]
    cog_settings = {"probabilities": probs, "ticket": {"rows": 2, "columns": 3}}

    # deterministic sheet we'll return from random.choices
    sheet = ["🌮", "🍎", "🌮", "🍎", "🌮", "🍎"]
    monkeypatch.setattr("bot.cogs.pulltab.random.choices", lambda symbols, weights, k: sheet)

    # identity helper id is mocked by conftest fixture; set a deterministic return
    cog.identity_helper.id.return_value = "ID-TEST-1"

    code, ticket_output = cog._generate_ticket(1, 10, cog_settings, multiplier=1)

    assert code == "ID-TEST-1"
    assert code in ticket_output
    # should have 2 rows (we configured rows=2) represented with separator lines
    assert ticket_output.count("||") >= 4  # each row emits two pipe boundaries
    assert code in cog.ticket_codes_cache
    # Ensure the DB save call stored ticket rows as strings (not nested lists)
    cog.pulltabs_db.save_ticket.assert_called_once()
    saved_payload = cog.pulltabs_db.save_ticket.call_args[0][0]
    assert isinstance(saved_payload.get("ticket"), list)
    assert all(isinstance(row, str) for row in saved_payload.get("ticket"))
    assert saved_payload.get("ticket")[0] == "🌮🍎🌮"


def test_calculate_multiplier_behavior(cog):
    # Default multiplier with requested = 1 should be 1.0
    assert cog._calculate_multiplier(1, base_increase=0.5) == 1.0

    # base_increase <= 0 should return 1.0 regardless of requested value
    assert cog._calculate_multiplier(5, base_increase=0.0) == 1.0

    # Example calculations for typical base increase values
    assert cog._calculate_multiplier(2, base_increase=0.5) == 2.0
    assert cog._calculate_multiplier(5, base_increase=0.5) == 3.5
    # A 10-point multiplier with base_increase of 0.1 is expected to double the payout
    assert cog._calculate_multiplier(10, base_increase=0.1) == pytest.approx(2.0)


def test_process_ticket_applies_effective_multiplier(cog):
    # Build probabilities with a single symbol that has single, double, and triple rules
    probs = [
        {
            "symbol": "🌮",
            "weight": 50,
            "rules": [
                {"match": "🌮", "reward": 100},
                {"match": "🌮🌮", "reward": 1000},
                {"match": "🌮🌮🌮", "reward": 10000},
            ],
        }
    ]

    # Single-line triple taco should award 1000 normally but be scaled by multiplier
    ticket = ["🌮🌮🌮"]
    is_winner, reward_no_mult, lines, indexes, _ = cog._process_ticket(ticket, {"probabilities": probs}, effective_multiplier=1.0)
    assert is_winner
    assert reward_no_mult == 10000

    # Apply a 50% increase multiplier (effective_multiplier = 1.5) and ensure rounding occurs to int
    is_winner, reward_with_mult, lines, indexes, _ = cog._process_ticket(ticket, {"probabilities": probs}, effective_multiplier=1.5)
    assert is_winner
    # 10000 * 1.5 = 15000
    assert reward_with_mult == 15000
    assert indexes == [0]


def test_generate_ticket_saves_effective_multiplier(cog, monkeypatch):
    # Use deterministic symbols and make identity deterministic
    probs = [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}]
    cog_settings = {"probabilities": probs, "ticket": {"rows": 1, "columns": 3}, "multiplier": {"base_increase": 0.5, "max": 100}}

    # deterministic sheet we'll return from random.choices
    sheet = ["🌮", "🌮", "🌮"]
    monkeypatch.setattr("bot.cogs.pulltab.random.choices", lambda symbols, weights, k: sheet)
    cog.identity_helper.id.return_value = "ID-MULT"

    # Save should capture the calculated multiplier
    code, ticket_output = cog._generate_ticket(1, 2, cog_settings, multiplier=2)

    saved_payload = cog.pulltabs_db.save_ticket.call_args[0][0]
    # 2 points with base_increase=0.5 => 1 + (2 * 0.5) == 2.0 (apply per point)
    assert saved_payload.get("multiplier") == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_process_pulltab_purchase_forwards_multiplier(cog, monkeypatch):
    # Ensure _generate_ticket receives the multiplier requested by the buyer.
    cog.taco_helper.get_taco_count = MagicMock(return_value=10000)

    # compose cog settings with a base_increase so multiplier will be used in saved payload
    probs = [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}]
    cog_settings = {"probabilities": probs, "ticket": {"rows": 1, "columns": 3}, "purchase": {"cost": 10, "max": 5, "multiplier": {"max": 100, "base_increase": 0.5}}}

    # get_cog_settings is invoked by _process_pulltab_purchase
    cog.get_cog_settings = MagicMock(return_value={**cog_settings, "purchase": cog_settings["purchase"]})

    # deterministic random choices + deterministic identity code
    monkeypatch.setattr("bot.cogs.pulltab.random.choices", lambda symbols, weights, k: ["🌮"] * 3)
    cog.identity_helper.id.return_value = "ID-MULT-TEST"

    # Use a fake interaction with minimal attributes expected by the method
    ctx = MagicMock(spec=Interaction)
    ctx.guild = MagicMock()
    ctx.guild.id = 7777
    ctx.user = MagicMock()
    ctx.user.id = 4444
    ctx.response = MagicMock()
    ctx.response.send_message = AsyncMock()

    # entity helper should return a user for purchase
    cog.entity_helper.get_or_fetch_user.return_value = MagicMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=3)

    # The saved ticket should include the calculated multiplier as computed by _calculate_multiplier
    # 3 points with base_increase=0.5 => 1 + (3 * 0.5) == 2.5
    saved_payload = cog.pulltabs_db.save_ticket.call_args[0][0]
    # 3 points with base_increase=0.5 => 1 + (3-1)*0.5 == 2.0
    assert saved_payload.get("multiplier") == pytest.approx(2.5)


@pytest.mark.asyncio
async def test_process_pulltab_purchase_with_multiplier_10_yields_2(cog, monkeypatch):
    # Test that when buyers select multiplier=10 and base_increase=0.1 the stored multiplier is 2.0
    cog.taco_helper.get_taco_count = MagicMock(return_value=10000)

    probs = [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}]
    purchase = {"cost": 10, "max": 5}
    multiplier = {"max": 100, "base_increase": 0.1}
    cog_settings = {"probabilities": probs, "ticket": {"rows": 1, "columns": 3}, "purchase": purchase, "multiplier": multiplier}

    cog.get_cog_settings = MagicMock(return_value={**cog_settings, "purchase": purchase, "multiplier": multiplier})

    monkeypatch.setattr("bot.cogs.pulltab.random.choices", lambda symbols, weights, k: ["🌮"] * 3)
    cog.identity_helper.id.return_value = "ID-MULT-10-CTX"

    ctx = MagicMock(spec=Interaction)
    ctx.guild = MagicMock()
    ctx.guild.id = 7777
    ctx.user = MagicMock()
    ctx.user.id = 4444
    ctx.response = MagicMock()
    ctx.response.send_message = AsyncMock()

    cog.entity_helper.get_or_fetch_user.return_value = MagicMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=10)

    saved_payload = cog.pulltabs_db.save_ticket.call_args[0][0]
    assert saved_payload.get("multiplier") == pytest.approx(2.0)


def test_generate_ticket_stores_expected_multiplier_for_10_points(cog, monkeypatch):
    # Ensure a 10x multiplier with base increase 0.1 yields an effective multiplier of 2.0
    probs = [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}]
    cog_settings = {"probabilities": probs, "ticket": {"rows": 1, "columns": 3}, "multiplier": {"base_increase": 0.1, "max": 100}}

    # deterministic sheet we'll return from random.choices
    sheet = ["🌮", "🌮", "🌮"]
    monkeypatch.setattr("bot.cogs.pulltab.random.choices", lambda symbols, weights, k: sheet)
    cog.identity_helper.id.return_value = "ID-MULT-10"

    code, ticket_output = cog._generate_ticket(1, 2, cog_settings, multiplier=10)

    saved_payload = cog.pulltabs_db.save_ticket.call_args[0][0]
    assert saved_payload.get("multiplier") == 2.0


def test_redeem_ticket_updates_redeemed_at_and_returns_reward(cog, monkeypatch):
    # Prepare a ticket that has not yet been redeemed
    ticket = PullTabTicketEntry(
        guild_id=1,
        user_id=2,
        code="CODE-RED",
        ticket=["🌮🍊🍎","🍀🍊🍎"],
        redeemed_at=None,
        reward=250,
        multiplier=1,
    )

    cog.pulltabs_db.get_ticket = MagicMock(return_value=ticket)
    cog.pulltabs_db.update_ticket = MagicMock()
    monkeypatch.setattr("bot.cogs.pulltab.utils.get_timestamp", lambda: 123456)

    success, reward, message = cog._redeem_ticket(1, 2, "CODE-RED")

    assert success is True
    assert reward == 250
    cog.pulltabs_db.update_ticket.assert_called_once_with(1, 2, "CODE-RED", {"redeemed_at": 123456})


def test_redeem_ticket_already_redeemed_returns_false(cog):
    ticket = PullTabTicketEntry(
        guild_id=5,
        user_id=6,
        code="CODE-ALR",
        ticket=["🌮🍎🍎"],
        redeemed_at=555,
        reward=100,
    )
    cog.pulltabs_db.get_ticket = MagicMock(return_value=ticket)
    cog.pulltabs_db.update_ticket = MagicMock()

    success, reward, message = cog._redeem_ticket(5, 6, "CODE-ALR")
    assert success is False
    assert reward == 0
    # update_ticket should not be called for already redeemed
    assert cog.pulltabs_db.update_ticket.call_count == 0


def test_redeem_ticket_invalid_code_returns_false(cog):
    cog.pulltabs_db.get_ticket = MagicMock(return_value=None)
    cog.pulltabs_db.update_ticket = MagicMock()

    success, reward, message = cog._redeem_ticket(7, 8, "NO-CODE")

    assert success is False
    assert reward == 0
    assert cog.pulltabs_db.update_ticket.call_count == 0


def test_generate_ticket_will_retry_on_duplicate_code(cog, monkeypatch):
    probs = [{"symbol": "🌮", "weight": 1, "rules": []}]
    cog_settings = {"probabilities": probs, "ticket": {"rows": 1, "columns": 3}}

    # deterministic sheet
    monkeypatch.setattr("bot.cogs.pulltab.random.choices", lambda symbols, weights, k: ["🌮", "🌮", "🌮"])

    # Force first ID to already exist => next call returns a unique id
    cog.ticket_codes_cache.add("ID-DUP")
    cog.identity_helper.id.side_effect = ["ID-DUP", "ID-UNIQUE"]

    code, ticket_output = cog._generate_ticket(1, 10, cog_settings, multiplier=1)

    assert code == "ID-UNIQUE"
    assert code in ticket_output
    assert "ID-DUP" in cog.ticket_codes_cache
    assert "ID-UNIQUE" in cog.ticket_codes_cache


def test_generate_ticket_calls_identity_helper_with_min_max(cog):
    probs = [{"symbol": "🌮", "weight": 1, "rules": []}]
    cog_settings = {"probabilities": probs, "ticket": {"rows": 1, "columns": 3}}

    cog.identity_helper.id = MagicMock(return_value="ID-ARGS")

    code, _ = cog._generate_ticket(1, 10, cog_settings, multiplier=1)

    assert code == "ID-ARGS"
    # ensure min and max are passed to the identity helper
    cog.identity_helper.id.assert_called()
    # inspect call args for min and max keyword args if available
    found = any((call.kwargs.get("min") == 8 and call.kwargs.get("max") == 16) for call in cog.identity_helper.id.call_args_list)
    assert found, "identity_helper.id was not called with min=8 and max=16"
