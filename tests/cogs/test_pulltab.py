from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.cogs.pulltab import PullTabCog
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from discord import Interaction


@pytest.fixture
def cog(bot, settings, message_helper, permissions, identity_helper, pulltabs_db, taco_helper, entity_helper, pulltab_helper):
    return PullTabCog(
        bot=bot,
        settings=settings,
        message_helper=message_helper,
        permissions=permissions,
        identity_helper=identity_helper,
        taco_helper=taco_helper,
        entity_helper=entity_helper,
        pulltabs_db=pulltabs_db,
        pulltab_helper=pulltab_helper,
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


def make_cog_settings():
    return {
        "enabled": True,
        "probabilities": make_probabilities(),
        "ticket": {"rows": 1, "columns": 3},
        "purchase": {"cost": 10, "max": 5},
        "multiplier": {"max": 100, "base_increase": 0.5},
    }


def test_exact_full_line_match(cog, pulltab_helper):
    cog_settings = make_cog_settings()
    ticket = ["🌮🌮🌮"]
    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)
    assert is_winner
    assert reward == 10000
    assert any("🌮🌮🌮" in x for x in lines)
    assert lines == [{"🌮🌮🌮": 10000}]


def test_two_tacos_any_order_match(cog, pulltab_helper):
    cog_settings = make_cog_settings()
    ticket = ["🌮🍎🌮"]
    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)
    assert is_winner
    assert reward == 1000
    assert any("🌮🌮" in x for x in lines)
    assert lines == [{"🌮🌮": 1000}]


def test_no_two_tacos(cog, pulltab_helper):
    cog_settings = make_cog_settings()
    ticket = ["🌮🍎🍉"]
    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)
    # single taco should award the single-symbol reward
    assert is_winner
    assert reward == 100
    assert any("🌮" in x for x in lines)
    assert lines == [{"🌮": 100}]


def test_multiple_rule_matches(cog, pulltab_helper):
    # Two tacos -> should match the highest rule for the symbol (two-taco rule)
    cog_settings = make_cog_settings()
    # add small reward for single taco to ensure both are counted
    ticket = ["🌮🌮🍎"]
    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)
    # should win for the double-taco rule only (avoid double-counting)
    assert is_winner
    assert any("🌮🌮" in x for x in lines)
    assert reward == 1000
    assert lines == [{"🌮🌮": 1000}]


def test_multiline_ticket_with_skull_blocks(cog, pulltab_helper):
    cog_settings = make_cog_settings()
    # Build probabilities with skull rule that denies payouts
    probs = [
        {"symbol": "🌮", "weight": 50, "rules": [{"match": "🌮", "reward": 100}]},
        {"symbol": "🍊", "weight": 30, "rules": []},
        {"symbol": "💀", "weight": 1, "rules": [{"match": "💀", "reward": 0, "multiplier": 0}]},
        {"symbol": "🍊", "weight": 10, "rules": [{"match": "🍊🍊", "reward": 50}]},
    ]
    cog_settings["probabilities"] = probs

    ticket = ["💀🍊🍊", "🍊🍒🍇", "🍎🌮🍒", "🍉🍇💀", "🍊🌮🍇"]

    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)
    assert is_winner
    # Lines 3 and 5 have single taco each (100 + 100)
    assert reward == 200
    assert len(lines) == 2
    assert lines == [{"🌮": 100}, {"🌮": 100}]


def test_complex_multiline_awards_with_skull(cog, pulltab_helper):
    cog_settings = make_cog_settings()
    probs = [
        {"symbol": "🌮", "weight": 50, "rules": [{"match": "🌮", "reward": 100}, {"match": "🌮🌮", "reward": 1000}]},
        {"symbol": "💀", "weight": 1, "rules": [{"match": "💀", "reward": 0, "multiplier": 0}]},
    ]
    cog_settings["probabilities"] = probs

    ticket = [
        "🌮🌮🍉",  # 1000
        "🌮🍉🌮",  # 1000
        "🌮🌮💀",  # 0 because skull present
        "🍎🍀🍊",  # 0 (no rule for combo)
        "🍀🍀🌮",  # 100 (single taco = 100)  <-- Example had 100
    ]

    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)
    assert is_winner
    assert reward == 2100
    assert lines == [{"🌮🌮": 1000}, {"🌮🌮": 1000}, {"🌮": 100}]


def test_real_probabilities_triple_matches_and_skull_block(cog, pulltab_helper):
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
    cog_settings = make_cog_settings()
    cog_settings["probabilities"] = probs

    # Single line triple clover
    ticket = ["🍀🍀🍀"]
    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)
    assert is_winner
    assert reward == 5000
    assert lines == [{"🍀🍀🍀": 5000}]

    # Skull blocks a line even when clover is present
    ticket = ["🍀💀🍀"]
    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)
    assert not is_winner or reward == 0
    assert lines == []

    # Triple taco should be recognized
    ticket = ["🌮🌮🌮"]
    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)
    assert is_winner
    assert reward == 10000
    assert lines == [{"🌮🌮🌮": 10000}]


def test_generate_ticket_adds_code_and_returns_output(cog, pulltab_helper, identity_helper, pulltabs_db, monkeypatch):
    # Build simple probabilities and a small ticket grid for deterministic output
    probs = [{"symbol": "🌮", "weight": 1, "rules": []}, {"symbol": "🍎", "weight": 1, "rules": []}]
    ticket_settings = {"rows": 2, "columns": 3}
    cog_settings = make_cog_settings()
    cog_settings["probabilities"] = probs
    cog_settings["ticket"] = ticket_settings

    # deterministic sheet we'll return from random.choices
    sheet = ["🌮", "🍎", "🌮", "🍎", "🌮", "🍎"]
    monkeypatch.setattr("bot.lib.helpers.pulltab_helper.random.choices", lambda symbols, weights, k: sheet)

    # identity helper id is mocked by conftest fixture; set a deterministic return
    identity_helper.id.return_value = "ID-TEST-1"

    code, ticket_entry = pulltab_helper.generate_ticket(guild_id=1, user_id=10, cog_settings=cog_settings, multiplier=1)

    assert code == "ID-TEST-1"
    assert ticket_entry.code == code
    # should have 2 rows (we configured rows=2)
    assert len(ticket_entry.ticket) == 2
    assert code in pulltab_helper.ticket_codes_cache
    # Ensure the DB save call stored ticket rows as strings (not nested lists)
    pulltabs_db.save_ticket.assert_called_once()
    saved_payload = pulltabs_db.save_ticket.call_args[0][0]
    assert isinstance(saved_payload.get("ticket"), list)
    assert all(isinstance(row, str) for row in saved_payload.get("ticket"))
    assert saved_payload.get("ticket")[0] == "🌮🍎🌮"


def test_calculate_multiplier_behavior(cog, pulltab_helper):
    # Default multiplier with requested = 1 should be 1.0
    assert pulltab_helper.calculate_multiplier(1, base_increase=0.5) == 1.0

    # base_increase <= 0 should return 1.0 regardless of requested value
    assert pulltab_helper.calculate_multiplier(5, base_increase=0.0) == 1.0

    # Example calculations for typical base increase values
    assert pulltab_helper.calculate_multiplier(2, base_increase=0.5) == 2.0
    assert pulltab_helper.calculate_multiplier(5, base_increase=0.5) == 3.5
    # A 10-point multiplier with base_increase of 0.1 is expected to double the payout
    assert pulltab_helper.calculate_multiplier(10, base_increase=0.1) == pytest.approx(2.0)


def test_process_ticket_applies_effective_multiplier(cog, pulltab_helper):
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
    cog_settings = make_cog_settings()
    cog_settings["probabilities"] = probs

    # Single-line triple taco should award 1000 normally but be scaled by multiplier
    ticket = ["🌮🌮🌮"]
    is_winner, reward_no_mult, lines = pulltab_helper.process_ticket(
        ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0
    )
    assert is_winner
    assert reward_no_mult == 10000
    assert lines == [{"🌮🌮🌮": 10000}]
    # Apply a 50% increase multiplier (effective_multiplier = 1.5) and ensure rounding occurs to int
    is_winner, reward_with_mult, lines = pulltab_helper.process_ticket(
        ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.5
    )
    assert is_winner
    # 10000 * 1.5 = 15000
    assert reward_with_mult == 15000
    assert lines == [{"🌮🌮🌮": 15000}]


def test_generate_ticket_saves_effective_multiplier(cog, pulltab_helper, identity_helper, pulltabs_db, monkeypatch):
    # Use deterministic symbols and make identity deterministic
    probs = [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}]
    cog_settings = {
        "probabilities": probs,
        "ticket": {"rows": 1, "columns": 3},
        "multiplier": {"base_increase": 0.5, "max": 100},
    }

    # deterministic sheet we'll return from random.choices
    sheet = ["🌮", "🌮", "🌮"]
    monkeypatch.setattr("bot.lib.helpers.pulltab_helper.random.choices", lambda symbols, weights, k: sheet)
    identity_helper.id.return_value = "ID-MULT"

    # Save should capture the calculated multiplier
    code, ticket_entry = pulltab_helper.generate_ticket(guild_id=1, user_id=2, cog_settings=cog_settings, multiplier=2)

    saved_payload = pulltabs_db.save_ticket.call_args[0][0]
    # 2 points with base_increase=0.5 => 1 + (2 * 0.5) == 2.0 (apply per point)
    assert saved_payload.get("effective_multiplier") == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_process_pulltab_purchase_forwards_multiplier(cog, pulltab_helper, taco_helper, identity_helper, pulltabs_db, monkeypatch):
    # Ensure generate_ticket receives the multiplier requested by the buyer.
    taco_helper.get_taco_count = MagicMock(return_value=10000)

    # compose cog settings with a base_increase so multiplier will be used in saved payload
    probs = [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}]
    cog_settings = {
        "probabilities": probs,
        "ticket": {"rows": 1, "columns": 3},
        "purchase": {"cost": 10, "max": 5},
        "multiplier": {"max": 100, "base_increase": 0.5},
    }

    # get_cog_settings is invoked by _process_pulltab_purchase
    cog.get_cog_settings = MagicMock(return_value={**cog_settings, "purchase": cog_settings["purchase"]})

    # deterministic random choices + deterministic identity code
    monkeypatch.setattr("bot.lib.helpers.pulltab_helper.random.choices", lambda symbols, weights, k: ["🌮"] * 3)
    identity_helper.id.return_value = "ID-MULT-TEST"

    # Use a fake interaction with minimal attributes expected by the method
    ctx = MagicMock(spec=Interaction)
    ctx.guild = MagicMock()
    ctx.guild.id = 7777
    ctx.user = MagicMock()
    ctx.user.id = 4444
    ctx.response = MagicMock()
    ctx.response.is_done = MagicMock(return_value=False)
    ctx.response.defer = AsyncMock()
    ctx.response.send_message = AsyncMock()
    ctx.followup = MagicMock()
    ctx.followup.send = AsyncMock()

    # entity helper should return a user for purchase
    cog.entity_helper.get_or_fetch_user.return_value = MagicMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=3)

    # The saved ticket should include the calculated multiplier as computed by calculate_multiplier
    # 3 points with base_increase=0.5 => 1 + (3 * 0.5) == 2.5
    saved_payload = pulltabs_db.save_ticket.call_args[0][0]
    # 3 points with base_increase=0.5 => 1 + (3-1)*0.5 == 2.0
    assert saved_payload.get("effective_multiplier") == pytest.approx(2.5)
    assert saved_payload.get("purchase_multiplier") == 3
    assert saved_payload.get("cost") == 10 * 3  # base cost 10 multiplied by purchase multiplier 3


@pytest.mark.asyncio
async def test_process_pulltab_purchase_with_multiplier_10_yields_2(cog, pulltab_helper, taco_helper, identity_helper, pulltabs_db, monkeypatch):
    # Test that when buyers select multiplier=10 and base_increase=0.1 the stored multiplier is 2.0
    taco_helper.get_taco_count = MagicMock(return_value=10000)

    probs = [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}]
    purchase = {"cost": 10, "max": 5}
    multiplier = {"max": 100, "base_increase": 0.1}
    cog_settings = {
        "probabilities": probs,
        "ticket": {"rows": 1, "columns": 3},
        "purchase": purchase,
        "multiplier": multiplier,
    }

    cog.get_cog_settings = MagicMock(return_value={**cog_settings, "purchase": purchase, "multiplier": multiplier})

    monkeypatch.setattr("bot.lib.helpers.pulltab_helper.random.choices", lambda symbols, weights, k: ["🌮"] * 3)
    identity_helper.id.return_value = "ID-MULT-10-CTX"

    ctx = MagicMock(spec=Interaction)
    ctx.guild = MagicMock()
    ctx.guild.id = 7777
    ctx.user = MagicMock()
    ctx.user.id = 4444
    ctx.response = MagicMock()
    ctx.response.is_done = MagicMock(return_value=False)
    ctx.response.defer = AsyncMock()
    ctx.response.send_message = AsyncMock()
    ctx.followup = MagicMock()
    ctx.followup.send = AsyncMock()

    cog.entity_helper.get_or_fetch_user.return_value = MagicMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=10)

    saved_payload = pulltabs_db.save_ticket.call_args[0][0]
    assert saved_payload.get("effective_multiplier") == pytest.approx(2.0)
    assert saved_payload.get("purchase_multiplier") == 10
    assert saved_payload.get("cost") == 10 * 10  # base cost 10 multiplied by purchase multiplier 10


def test_generate_ticket_stores_expected_multiplier_for_10_points(cog, pulltab_helper, identity_helper, pulltabs_db, monkeypatch):
    # Ensure a 10x multiplier with base increase 0.1 yields an effective multiplier of 2.0
    probs = [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}]
    cog_settings = {
        "probabilities": probs,
        "ticket": {"rows": 1, "columns": 3},
        "multiplier": {"base_increase": 0.1, "max": 100},
    }

    # deterministic sheet we'll return from random.choices
    sheet = ["🌮", "🌮", "🌮"]
    monkeypatch.setattr("bot.lib.helpers.pulltab_helper.random.choices", lambda symbols, weights, k: sheet)
    identity_helper.id.return_value = "ID-MULT-10"

    code, ticket_entry = pulltab_helper.generate_ticket(guild_id=1, user_id=2, cog_settings=cog_settings, multiplier=10)

    saved_payload = pulltabs_db.save_ticket.call_args[0][0]
    assert saved_payload.get("effective_multiplier") == 2.0


def test_redeem_ticket_updates_redeemed_at_and_returns_reward(cog, pulltab_helper, pulltabs_db, monkeypatch):
    # Prepare a ticket that has not yet been redeemed
    ticket = PullTabTicketEntry(
        guild_id=1,
        user_id=2,
        code="CODE-RED",
        ticket=["🌮🍊🍎", "🍀🍊🍎"],
        redeemed_at=None,
        reward=250,
        effective_multiplier=1,
        purchase_multiplier=1,
        cost=10,
    )

    pulltabs_db.get_ticket = MagicMock(return_value=ticket)
    pulltabs_db.update_ticket = MagicMock()
    monkeypatch.setattr("bot.lib.utils.get_timestamp", lambda: 123456)

    success, reward, message = pulltab_helper.redeem_ticket(1, 2, "CODE-RED")

    assert success is True
    assert reward == 250
    pulltabs_db.update_ticket.assert_called_once_with(1, 2, "CODE-RED", {"redeemed_at": 123456})


def test_redeem_ticket_already_redeemed_returns_false(cog, pulltab_helper, pulltabs_db):
    ticket = PullTabTicketEntry(guild_id=5, user_id=6, code="CODE-ALR", ticket=["🌮🍎🍎"], redeemed_at=555, reward=100)
    pulltabs_db.get_ticket = MagicMock(return_value=ticket)
    pulltabs_db.update_ticket = MagicMock()

    success, reward, message = pulltab_helper.redeem_ticket(guild_id=5, user_id=6, code="CODE-ALR")
    assert success is False
    assert reward == 0
    # update_ticket should not be called for already redeemed
    assert pulltabs_db.update_ticket.call_count == 0


def test_redeem_ticket_invalid_code_returns_false(cog, pulltab_helper, pulltabs_db):
    pulltabs_db.get_ticket = MagicMock(return_value=None)
    pulltabs_db.update_ticket = MagicMock()

    success, reward, message = pulltab_helper.redeem_ticket(guild_id=7, user_id=8, code="NO-CODE")

    assert success is False
    assert reward == 0
    assert pulltabs_db.update_ticket.call_count == 0


def test_generate_ticket_will_retry_on_duplicate_code(cog, pulltab_helper, identity_helper, monkeypatch):
    probs = [{"symbol": "🌮", "weight": 1, "rules": []}]
    cog_settings = make_cog_settings()
    cog_settings["probabilities"] = probs

    # deterministic sheet
    monkeypatch.setattr("bot.lib.helpers.pulltab_helper.random.choices", lambda symbols, weights, k: ["🌮", "🌮", "🌮"])

    # Force first ID to already exist => next call returns a unique id
    pulltab_helper.ticket_codes_cache.add("ID-DUP")
    identity_helper.id.side_effect = ["ID-DUP", "ID-UNIQUE"]

    code, ticket_entry = pulltab_helper.generate_ticket(guild_id=1, user_id=10, cog_settings=cog_settings, multiplier=1)

    assert code == "ID-UNIQUE"
    assert ticket_entry.code == code
    assert "ID-DUP" in pulltab_helper.ticket_codes_cache
    assert "ID-UNIQUE" in pulltab_helper.ticket_codes_cache


def test_generate_ticket_calls_identity_helper_with_min_max(cog, pulltab_helper, identity_helper):
    probs = [{"symbol": "🌮", "weight": 1, "rules": []}]
    cog_settings = {"probabilities": probs, "ticket": {"rows": 1, "columns": 3}}

    identity_helper.id = MagicMock(return_value="ID-ARGS")

    code, _ = pulltab_helper.generate_ticket(guild_id=1, user_id=10, cog_settings=cog_settings, multiplier=1)

    assert code == "ID-ARGS"
    # ensure min and max are passed to the identity helper
    identity_helper.id.assert_called()
    # inspect call args for min and max keyword args if available
    found = any(
        (call.kwargs.get("min") == 8 and call.kwargs.get("max") == 16) for call in identity_helper.id.call_args_list
    )
    assert found, "identity_helper.id was not called with min=8 and max=16"


# Tests for info message builders


def test_build_payout_message_with_multiplier_1(cog):
    cog_settings = {
        "probabilities": [
            {"symbol": "🌮", "weight": 50, "rules": [{"match": "🌮🌮🌮", "reward": 10000}]},
            {"symbol": "🍀", "weight": 30, "rules": [{"match": "🍀🍀", "reward": 500}]},
        ],
        "multiplier": {"base_increase": 0.5, "max": 100},
    }

    message = cog._build_payout_message(cog_settings, multiplier=1)

    assert "Payouts (based on multiplier x1)" in message
    assert "🌮🌮🌮 -> 10000" in message
    assert "🍀🍀 -> 500" in message


def test_build_payout_message_with_higher_multiplier(cog):
    cog_settings = {
        "probabilities": [{"symbol": "🌮", "weight": 50, "rules": [{"match": "🌮🌮🌮", "reward": 10000}]}],
        "multiplier": {"base_increase": 0.5, "max": 100},
    }

    message = cog._build_payout_message(cog_settings, multiplier=2)

    assert "Payouts (based on multiplier x2)" in message
    # 10000 * (1 + 2*0.5) = 10000 * 2.0 = 20000
    assert "🌮🌮🌮 -> 20000" in message


def test_build_payout_message_with_rule_multiplier(cog):
    cog_settings = {
        "probabilities": [{"symbol": "💀", "weight": 10, "rules": [{"match": "💀", "reward": 0, "multiplier": 0}]}],
        "multiplier": {"base_increase": 0.1, "max": 100},
    }

    message = cog._build_payout_message(cog_settings, multiplier=1)

    assert "💀 -> line multiplier x0" in message


def test_build_probability_message(cog):
    probabilities = [{"symbol": "🌮", "weight": 50}, {"symbol": "🍀", "weight": 30}, {"symbol": "🍎", "weight": 20}]

    message = cog._build_probability_message(probabilities)

    assert "Probabilities:" in message
    assert "🌮: 50.00%" in message
    assert "🍀: 30.00%" in message
    assert "🍎: 20.00%" in message


def test_build_probability_message_empty_probabilities(cog):
    probabilities = []

    message = cog._build_probability_message(probabilities)

    assert "Probabilities:" in message


def test_build_cost_multiplier_message(cog):
    cog_settings = {"purchase": {"cost": 100, "max": 5}, "multiplier": {"base_increase": 0.5, "max": 100}}

    message = cog._build_cost_multiplier_message(cog_settings, multiplier=1)

    assert "Cost per ticket: 100 tacos" in message
    assert "Max tickets per purchase: 5" in message
    assert "Multiplier: 1" in message
    assert "max 100" in message
    assert "How multiplier works:" in message


def test_build_cost_multiplier_message_with_higher_multiplier(cog):
    cog_settings = {"purchase": {"cost": 50, "max": 10}, "multiplier": {"base_increase": 0.1, "max": 50}}

    message = cog._build_cost_multiplier_message(cog_settings, multiplier=5)

    # Cost: 50 * 5 = 250
    assert "Cost per ticket: 250 tacos (with multiplier x5)" in message
    assert "Multiplier: 5 (max 50)" in message


# Tests for _process_pulltab_info


@pytest.mark.asyncio
async def test_process_pulltab_info_with_context(cog):
    cog_settings = {
        "probabilities": [{"symbol": "🌮", "weight": 50, "rules": [{"match": "🌮", "reward": 100}]}],
        "purchase": {"cost": 10, "max": 5},
        "multiplier": {"base_increase": 0.5, "max": 100},
    }
    cog.get_cog_settings = MagicMock(return_value=cog_settings)

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 1111
    ctx.send = AsyncMock()

    await cog._process_pulltab_info(ctx, multiplier=1)

    ctx.send.assert_called_once()
    call_args = ctx.send.call_args
    message = call_args[0][0]
    assert "Cost per ticket: 10 tacos" in message
    assert "Payouts" in message
    assert "Probabilities" in message


@pytest.mark.asyncio
async def test_process_pulltab_info_with_interaction(cog):
    cog_settings = {
        "probabilities": [{"symbol": "🍀", "weight": 30, "rules": [{"match": "🍀🍀", "reward": 500}]}],
        "purchase": {"cost": 20, "max": 3},
        "multiplier": {"base_increase": 0.2, "max": 50},
    }
    cog.get_cog_settings = MagicMock(return_value=cog_settings)

    ctx = MagicMock(spec=Interaction)
    ctx.guild = MagicMock()
    ctx.guild.id = 2222
    ctx.response = MagicMock()
    ctx.response.is_done = MagicMock(return_value=False)
    ctx.response.defer = AsyncMock()
    ctx.response.send_message = AsyncMock()

    await cog._process_pulltab_info(ctx, multiplier=2)

    ctx.response.send_message.assert_called_once()
    call_args = ctx.response.send_message.call_args
    message = call_args[0][0]
    # Cost: 20 * 2 = 40
    assert "Cost per ticket: 40 tacos (with multiplier x2)" in message
    assert "Payouts" in message


@pytest.mark.asyncio
async def test_process_pulltab_info_no_cog_settings(cog):
    cog.get_cog_settings = MagicMock(return_value=None)

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 3333
    ctx.send = AsyncMock()

    await cog._process_pulltab_info(ctx, multiplier=1)

    # Should return early without sending anything
    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_process_pulltab_info_handles_exception(cog):
    cog.get_cog_settings = MagicMock(side_effect=Exception("Test error"))

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 4444
    ctx.send = AsyncMock()

    # Should not raise, just log the error
    await cog._process_pulltab_info(ctx, multiplier=1)


# Tests for _process_pulltab_redeem


@pytest.mark.asyncio
async def test_process_pulltab_redeem_success_with_reward(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id=123))
    cog.settings.get_string = MagicMock(return_value="Redeemed successfully!")

    ticket = PullTabTicketEntry(
        guild_id=1, user_id=123, code="WIN-CODE", ticket=["🌮🌮🌮"], redeemed_at=None, reward=5000
    )

    cog.pulltabs_db.get_ticket = MagicMock(return_value=ticket)
    cog.pulltabs_db.update_ticket = MagicMock()
    cog.taco_helper.give_tacos = AsyncMock()

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 1
    ctx.author = MagicMock()
    ctx.author.id = 123
    ctx.send = AsyncMock()

    await cog._process_pulltab_redeem(ctx, code="WIN-CODE")

    cog.taco_helper.give_tacos.assert_called_once()
    ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_process_pulltab_redeem_success_no_reward(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id=456))
    cog.settings.get_string = MagicMock(return_value="No reward this time")

    ticket = PullTabTicketEntry(
        guild_id=2, user_id=456, code="LOSE-CODE", ticket=["🍎🍊🍉"], redeemed_at=None, reward=0
    )

    cog.pulltabs_db.get_ticket = MagicMock(return_value=ticket)
    cog.pulltabs_db.update_ticket = MagicMock()
    cog.taco_helper.give_tacos = AsyncMock()

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 2
    ctx.author = MagicMock()
    ctx.author.id = 456
    ctx.send = AsyncMock()

    await cog._process_pulltab_redeem(ctx, code="LOSE-CODE")

    cog.taco_helper.give_tacos.assert_not_called()
    ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_process_pulltab_redeem_already_redeemed(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id=789))
    cog.settings.get_string = MagicMock(return_value="Already redeemed")

    ticket = PullTabTicketEntry(
        guild_id=3, user_id=789, code="USED-CODE", ticket=["🌮🌮🌮"], redeemed_at=12345, reward=1000
    )

    cog.pulltabs_db.get_ticket = MagicMock(return_value=ticket)
    cog.pulltabs_db.update_ticket = MagicMock()
    cog.taco_helper.give_tacos = AsyncMock()

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 3
    ctx.author = MagicMock()
    ctx.author.id = 789
    ctx.send = AsyncMock()

    await cog._process_pulltab_redeem(ctx, code="USED-CODE")

    cog.taco_helper.give_tacos.assert_not_called()
    ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_process_pulltab_redeem_invalid_code(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id=999))
    cog.settings.get_string = MagicMock(return_value="Invalid code")

    cog.pulltabs_db.get_ticket = MagicMock(return_value=None)
    cog.taco_helper.give_tacos = AsyncMock()

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 4
    ctx.author = MagicMock()
    ctx.author.id = 999
    ctx.send = AsyncMock()

    await cog._process_pulltab_redeem(ctx, code="BAD-CODE")

    cog.taco_helper.give_tacos.assert_not_called()
    ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_process_pulltab_redeem_with_interaction(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id=111))
    cog.settings.get_string = MagicMock(return_value="Success message")

    ticket = PullTabTicketEntry(
        guild_id=5, user_id=111, code="INT-CODE", ticket=["🍀🍀🍀"], redeemed_at=None, reward=2500
    )

    cog.pulltabs_db.get_ticket = MagicMock(return_value=ticket)
    cog.pulltabs_db.update_ticket = MagicMock()
    cog.taco_helper.give_tacos = AsyncMock()

    ctx = MagicMock(spec=Interaction)
    ctx.guild = MagicMock()
    ctx.guild.id = 5
    ctx.user = MagicMock()
    ctx.user.id = 111
    ctx.response = MagicMock()
    ctx.response.is_done = MagicMock(return_value=False)
    ctx.response.defer = AsyncMock()
    ctx.response.send_message = AsyncMock()
    ctx.followup = MagicMock()
    ctx.followup.send = AsyncMock()

    await cog._process_pulltab_redeem(ctx, code="INT-CODE")

    cog.taco_helper.give_tacos.assert_called_once()
    # After defer, we use followup.send instead of response.send_message
    ctx.followup.send.assert_called_once()


@pytest.mark.asyncio
async def test_process_pulltab_redeem_empty_code(cog):
    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 6
    ctx.author = MagicMock()
    ctx.author.id = 222
    ctx.send = AsyncMock()

    # Empty code should just return without doing anything
    await cog._process_pulltab_redeem(ctx, code="")

    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_process_pulltab_redeem_handles_exception(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(side_effect=Exception("Test error"))
    cog.message_helper.notify_of_error = AsyncMock()

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 7
    ctx.author = MagicMock()
    ctx.author.id = 333
    ctx.send = AsyncMock()

    await cog._process_pulltab_redeem(ctx, code="ERROR-CODE")

    cog.message_helper.notify_of_error.assert_called_once()


@pytest.mark.asyncio
async def test_process_pulltab_redeem_bot_user_none(cog, monkeypatch):
    # Set bot.user to None to test early return
    monkeypatch.setattr(cog.bot, "user", None)

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 8
    ctx.send = AsyncMock()

    await cog._process_pulltab_redeem(ctx, code="TEST-CODE")

    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_process_pulltab_redeem_user_fetch_returns_none(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=None)

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 9
    ctx.author = MagicMock()
    ctx.author.id = 444
    ctx.send = AsyncMock()

    await cog._process_pulltab_redeem(ctx, code="TEST-CODE")

    ctx.send.assert_not_called()


# Tests for edge cases and helper methods


def test_clamp_below_min(cog):
    from bot.lib.helpers import Numbers
    result = Numbers.clamp(-5, 1, 10)
    assert result == 1


def test_clamp_above_max(cog):
    from bot.lib.helpers import Numbers
    result = Numbers.clamp(100, 1, 10)
    assert result == 10


def test_clamp_within_range(cog):
    from bot.lib.helpers import Numbers
    result = Numbers.clamp(5, 1, 10)
    assert result == 5


def test_validate_user_can_spend_success(cog, taco_helper):
    taco_helper.get_taco_count = MagicMock(return_value=1000)

    result = taco_helper.validate_user_can_spend(1, 2, 500)

    assert result is True


def test_validate_user_can_spend_insufficient_tacos(cog, bot):
    from bot.lib.helpers import TacoHelper
    taco_helper = TacoHelper(bot)
    taco_helper.get_taco_count = MagicMock(return_value=100)

    result = taco_helper.validate_user_can_spend(1, 2, 500)

    assert result is False


def test_validate_user_can_spend_none_taco_count(cog, bot):
    from bot.lib.helpers import TacoHelper
    taco_helper = TacoHelper(bot)
    taco_helper.get_taco_count = MagicMock(return_value=None)

    result = taco_helper.validate_user_can_spend(1, 2, 500)

    assert result is False


def test_redeem_ticket_marks_redeemed_even_with_no_reward(cog, pulltab_helper, pulltabs_db, monkeypatch):
    ticket = PullTabTicketEntry(
        guild_id=10, user_id=20, code="NO-REWARD", ticket=["🍊🍊🍊"], redeemed_at=None, reward=0
    )

    pulltabs_db.get_ticket = MagicMock(return_value=ticket)
    pulltabs_db.update_ticket = MagicMock()
    monkeypatch.setattr("bot.lib.utils.get_timestamp", lambda: 99999)

    success, reward, message = pulltab_helper.redeem_ticket(10, 20, "NO-REWARD")

    assert success is True
    assert reward == 0
    pulltabs_db.update_ticket.assert_called_once_with(10, 20, "NO-REWARD", {"redeemed_at": 99999})


@pytest.mark.asyncio
async def test_send_message_with_context(cog):
    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.send = AsyncMock()

    await cog._send_message(ctx, "Test message", ephemeral=True)

    ctx.send.assert_called_once_with("Test message")


@pytest.mark.asyncio
async def test_send_message_with_interaction(cog):
    ctx = MagicMock(spec=Interaction)
    ctx.response = MagicMock()
    ctx.response.is_done = MagicMock(return_value=False)
    ctx.response.send_message = AsyncMock()
    ctx.followup = MagicMock()
    ctx.followup.send = AsyncMock()

    await cog._send_message(ctx, "Test message", ephemeral=True)

    ctx.response.send_message.assert_called_once_with("Test message", ephemeral=True)


@pytest.mark.asyncio
async def test_send_message_invalid_context_type(cog):
    # Invalid context type should log error but not crash
    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.guild.id = 123
    # Don't set spec so it's neither Context nor Interaction

    await cog._send_message(ctx, "Test message")

    # Should not raise, just log
    # No way to assert the message wasn't sent since we have a mock


def test_process_ticket_with_unexpected_row_type(cog, pulltab_helper):
    # Test with an unexpected row type (int)
    probs = [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}]

    cog_settings = make_cog_settings()
    cog_settings["probabilities"] = probs

    # Unexpected format: int instead of string or list
    ticket = [12345]

    is_winner, reward, lines = pulltab_helper.process_ticket(ticket=ticket, cog_settings=cog_settings, effective_multiplier=1.0)

    # Should coerce to string then process
    # "12345" won't match any symbols so no winner
    assert not is_winner or reward == 0


# Tests for error paths in _process_pulltab_purchase


@pytest.mark.asyncio
async def test_process_pulltab_purchase_bot_user_none(cog, monkeypatch):
    monkeypatch.setattr(cog.bot, "user", None)

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 1
    ctx.send = AsyncMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=1)

    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_process_pulltab_purchase_invalid_context_type(cog):
    # Test with invalid context type
    ctx = "not a context"

    # Should just log error and return
    await cog._process_pulltab_purchase(ctx, count=1, multiplier=1)


@pytest.mark.asyncio
async def test_process_pulltab_purchase_user_is_bot(cog):
    cog.bot.user = MagicMock()
    cog.bot.user.id = 999

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 1
    ctx.author = MagicMock()
    ctx.author.id = 999  # Same as bot
    ctx.send = AsyncMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=1)

    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_process_pulltab_purchase_user_fetch_fails(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=None)

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 1
    ctx.author = MagicMock()
    ctx.author.id = 123
    ctx.send = AsyncMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=1)

    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_process_pulltab_purchase_no_cog_settings(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id=123))
    cog.taco_helper.get_taco_count = MagicMock(return_value=1000)
    cog.get_cog_settings = MagicMock(return_value=None)

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 1
    ctx.author = MagicMock()
    ctx.author.id = 123
    ctx.send = AsyncMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=1)

    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_process_pulltab_purchase_insufficient_funds(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id=123, mention="<@123>"))
    cog.taco_helper.get_taco_count = MagicMock(return_value=5)
    # Mock validate_user_can_spend to return False (insufficient funds)
    cog.taco_helper.validate_user_can_spend = MagicMock(return_value=False)
    cog.settings.get_string = MagicMock(return_value="Not enough tacos")

    cog_settings = {
        "probabilities": [{"symbol": "🌮", "weight": 1, "rules": [{"match": "🌮", "reward": 100}]}],
        "purchase": {"cost": 10, "max": 5},
        "multiplier": {"base_increase": 0.5, "max": 100},
        "ticket": {"rows": 1, "columns": 3},
    }
    cog.get_cog_settings = MagicMock(return_value=cog_settings)

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 1
    ctx.author = MagicMock()
    ctx.author.id = 123
    ctx.send = AsyncMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=1)

    ctx.send.assert_called_once()
    call_args = ctx.send.call_args
    assert "Not enough tacos" in call_args[0][0]


@pytest.mark.asyncio
async def test_process_pulltab_purchase_no_probabilities(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id=123))
    cog.taco_helper.get_taco_count = MagicMock(return_value=1000)

    cog_settings = {
        "probabilities": [],  # Empty probabilities
        "purchase": {"cost": 10, "max": 5},
        "multiplier": {"base_increase": 0.5, "max": 100},
        "ticket": {"rows": 1, "columns": 3},
    }
    cog.get_cog_settings = MagicMock(return_value=cog_settings)

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 1
    ctx.author = MagicMock()
    ctx.author.id = 123
    ctx.send = AsyncMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=1)

    # Should return early without sending message
    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_process_pulltab_purchase_exception_handling(cog):
    cog.entity_helper.get_or_fetch_user = AsyncMock(side_effect=Exception("Test error"))
    cog.message_helper.notify_of_error = AsyncMock()

    from discord.ext import commands

    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock()
    ctx.guild.id = 1
    ctx.author = MagicMock()
    ctx.author.id = 123
    ctx.send = AsyncMock()

    await cog._process_pulltab_purchase(ctx, count=1, multiplier=1)

    cog.message_helper.notify_of_error.assert_called_once()


# Test for setup function


@pytest.mark.asyncio
async def test_setup_function(bot):
    # Import the setup function
    from bot.cogs.pulltab import setup

    # Setup should not raise any errors
    await setup(bot)

    # Verify that add_cog was called
    bot.add_cog.assert_called_once()
