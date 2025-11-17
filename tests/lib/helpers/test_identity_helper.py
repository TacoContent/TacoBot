import string
import uuid

import pytest
from bot.lib.helpers.identity_helper import IdentityHelper


def test_uuid_is_valid_uuidv4_and_unique():
    helper = IdentityHelper()
    u1 = helper.uuid()
    u2 = helper.uuid()

    # Both should be strings that parse to a UUID
    assert isinstance(u1, str)
    assert isinstance(u2, str)

    parsed1 = uuid.UUID(u1)
    parsed2 = uuid.UUID(u2)

    assert parsed1.version == 4
    assert parsed2.version == 4

    # Typically two consecutive uuids are different
    assert u1 != u2


def test_id_default_length_range(monkeypatch):
    helper = IdentityHelper()

    # Force randint to return a known length so the test is deterministic
    monkeypatch.setattr('bot.lib.helpers.identity_helper.random.randint', lambda a, b: 10)

    value = helper.id()
    assert isinstance(value, str)
    assert len(value) == 10

    # All chars are from the allowed alphanumeric set
    assert all(ch in string.ascii_letters + string.digits for ch in value)


def test_id_respects_min_max(monkeypatch):
    helper = IdentityHelper()

    # Test with min==max
    monkeypatch.setattr('bot.lib.helpers.identity_helper.random.randint', lambda a, b: 2)
    monkeypatch.setattr('bot.lib.helpers.identity_helper.random.choices', lambda characters, k: ['A'] * k)

    value = helper.id(min=2, max=2)
    assert value == 'AA'

    # Test with a different fixed length
    monkeypatch.setattr('bot.lib.helpers.identity_helper.random.randint', lambda a, b: 6)
    monkeypatch.setattr('bot.lib.helpers.identity_helper.random.choices', lambda characters, k: list('abc123'))

    value2 = helper.id(min=6, max=6)
    # The monkeypatched choices returns a list, which the method joins
    assert value2 == 'abc123'


def test_id_min_greater_than_max_raises():
    helper = IdentityHelper()

    with pytest.raises(ValueError):
        helper.id(min=12, max=8)


def test_id_only_allowed_characters(monkeypatch):
    helper = IdentityHelper()

    # Use a deterministic length
    monkeypatch.setattr('bot.lib.helpers.identity_helper.random.randint', lambda a, b: 15)

    # Do not alter choices; use the real implementation so we can test allowed charset
    value = helper.id(min=15, max=15)
    assert len(value) == 15

    # Check that only letters and digits are present
    assert all(ch.isalnum() for ch in value)
