import pytest
from bot.cogs.pulltab import PullTabCog


@pytest.fixture
def cog(bot, settings, message_helper, permissions):
    return PullTabCog(bot=bot, settings=settings, message_helper=message_helper, permissions=permissions)


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
    ticket = [["🌮", "🌮", "🌮"]]
    is_winner, reward, lines = cog._process_ticket(ticket, {"probabilities": probs})
    assert is_winner
    assert reward == 10000
    assert any("🌮🌮🌮" in l for l in lines)


def test_two_tacos_any_order_match(cog):
    probs = make_probabilities()
    ticket = [["🌮", "🍎", "🌮"]]
    is_winner, reward, lines = cog._process_ticket(ticket, {"probabilities": probs})
    assert is_winner
    assert reward == 1000
    assert any("🌮🌮" in l for l in lines)


def test_no_two_tacos(cog):
    probs = make_probabilities()
    ticket = [["🌮", "🍎", "🍉"]]
    is_winner, reward, lines = cog._process_ticket(ticket, {"probabilities": probs})
    # single taco should award the single-symbol reward
    assert is_winner
    assert reward == 100
    assert any("🌮" in l for l in lines)


def test_multiple_rule_matches(cog):
    # Two tacos -> should match the highest rule for the symbol (two-taco rule)
    probs = make_probabilities()
    # add small reward for single taco to ensure both are counted
    ticket = [["🌮", "🌮", "🍎"]]
    is_winner, reward, lines = cog._process_ticket(ticket, {"probabilities": probs})
    # should win for the double-taco rule only (avoid double-counting)
    assert is_winner
    assert any("🌮🌮" in l for l in lines)
    assert reward == 1000
    assert not any("Matched 🌮 for 100" in l for l in lines)


def test_multiline_ticket_with_skull_blocks(cog):
    # Build probabilities with skull rule that denies payouts
    probs = [
        {"symbol": "🌮", "weight": 50, "rules": [{"match": "🌮", "reward": 100}]},
        {"symbol": "🍊", "weight": 30, "rules": []},
        {"symbol": "💀", "weight": 1, "rules": [{"match": "💀", "reward": 0, "multiplier": 0}]},
        {"symbol": "🍊", "weight": 10, "rules": [{"match": "🍊🍊", "reward": 50}]},
    ]

    ticket = [["💀", "🍊", "🍊"], ["🍊", "🍒", "🍇"], ["🍎", "🌮", "🍒"], ["🍉", "🍇", "💀"], ["🍊", "🌮", "🍇"]]

    is_winner, reward, lines = cog._process_ticket(ticket, {"probabilities": probs})
    assert is_winner
    # Lines 3 and 5 have single taco each (100 + 100)
    assert reward == 200
    assert len(lines) == 2


def test_complex_multiline_awards_with_skull(cog):
    probs = [
        {"symbol": "🌮", "weight": 50, "rules": [{"match": "🌮", "reward": 100}, {"match": "🌮🌮", "reward": 1000}]},
        {"symbol": "💀", "weight": 1, "rules": [{"match": "💀", "reward": 0, "multiplier": 0}]},
    ]

    ticket = [
        ["🌮", "🌮", "🍉"],  # 1000
        ["🌮", "🍉", "🌮"],  # 1000
        ["🌮", "🌮", "💀"],  # 0 because skull present
        ["🍎", "🍀", "🍊"],  # 0 (no rule for combo)
        ["🍀", "🍀", "🌮"],  # 100 (single taco = 100)  <-- Example had 100
    ]

    is_winner, reward, lines = cog._process_ticket(ticket, {"probabilities": probs})
    assert is_winner
    assert reward == 2100


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
    ticket = [["🍀", "🍀", "🍀"]]
    is_winner, reward, lines = cog._process_ticket(ticket, {"probabilities": probs})
    assert is_winner
    assert reward == 5000

    # Skull blocks a line even when clover is present
    ticket = [["🍀", "💀", "🍀"]]
    is_winner, reward, lines = cog._process_ticket(ticket, {"probabilities": probs})
    assert not is_winner or reward == 0

    # Triple taco should be recognized
    ticket = [["🌮", "🌮", "🌮"]]
    is_winner, reward, lines = cog._process_ticket(ticket, {"probabilities": probs})
    assert is_winner
    assert reward == 10000
