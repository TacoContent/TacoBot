from unittest.mock import MagicMock
import inspect
import re

import pytest

from bot.lib.mongodb.tacos import TacosDatabase


@pytest.fixture
def db():
    d = TacosDatabase()
    d.settings = MagicMock()
    d.settings.timezone = 'UTC'
    d.client = object()
    d.connection = MagicMock()
    d.log = MagicMock()
    return d


def test_remove_all_and_delete_error(db):
    db.connection.tacos.delete_many = MagicMock()
    db.remove_all_tacos(1, 2)
    assert db.connection.tacos.delete_many.called

    db.connection.tacos.delete_many = MagicMock(side_effect=RuntimeError('boom'))
    db.remove_all_tacos(1, 2)
    assert db.log.called


def test_add_tacos_new_and_existing(db):
    # get_tacos_count returns None -> treat as 0
    db.get_tacos_count = MagicMock(return_value=None)
    db.connection.tacos.update_one = MagicMock()
    res = db.add_tacos(1, 1, 5)
    assert res == 5
    assert db.connection.tacos.update_one.called

    # existing tacos
    db.get_tacos_count = MagicMock(return_value=3)
    db.connection.tacos.update_one = MagicMock()
    res = db.add_tacos(1, 1, 2)
    assert res == 5

    # exception path
    db.get_tacos_count = MagicMock(side_effect=RuntimeError('boom'))
    assert db.add_tacos(1, 1, 1) == 0
    assert db.log.called


def test_remove_tacos_and_bounds(db):
    # negative count early return
    assert db.remove_tacos(1, 1, -5) == 0

    # user absent -> treat as 0
    db.get_tacos_count = MagicMock(return_value=None)
    db.connection.tacos.update_one = MagicMock()
    res = db.remove_tacos(2, 3, 4)
    assert res == 0
    assert db.connection.tacos.update_one.called

    # user has fewer than to remove -> nothing below zero
    db.get_tacos_count = MagicMock(return_value=2)
    db.connection.tacos.update_one = MagicMock()
    res = db.remove_tacos(2, 3, 5)
    assert res == 0


def test_get_tacos_count_and_errors(db):
    db.connection.tacos.find_one = MagicMock(return_value=None)
    assert db.get_tacos_count(1, 2) is None

    db.connection.tacos.find_one = MagicMock(return_value={'count': 7})
    assert db.get_tacos_count(1, 2) == 7

    db.connection.tacos.find_one = MagicMock(side_effect=RuntimeError('boom'))
    assert db.get_tacos_count(1, 2) is None


def test_total_gifted_tacos(db):
    db.connection.taco_gifts.find = MagicMock(return_value=[{'count': 1}, {'count': 2}])
    assert db.get_total_gifted_tacos(1, 2) == 3

    db.connection.taco_gifts.find = MagicMock(return_value=None)
    assert db.get_total_gifted_tacos(1, 2) == 0

    db.connection.taco_gifts.find = MagicMock(side_effect=RuntimeError('boom'))
    assert db.get_total_gifted_tacos(1, 2) == 0


def test_add_taco_gift(db):
    db.connection.taco_gifts.insert_one = MagicMock()
    assert db.add_taco_gift(1, 2, 3) is True

    db.connection.taco_gifts.insert_one = MagicMock(side_effect=RuntimeError('boom'))
    assert db.add_taco_gift(1, 2, 3) is False


def test_reaction_and_find(db):
    db.connection.tacos_reactions.update_one = MagicMock()
    db.add_taco_reaction(1, 2, 3, 4)
    assert db.connection.tacos_reactions.update_one.called

    db.connection.tacos_reactions.find_one = MagicMock(return_value=None)
    assert db.get_taco_reaction(1, 2, 3, 4) is None

    db.connection.tacos_reactions.find_one = MagicMock(return_value={'x': 1})
    assert db.get_taco_reaction(1, 2, 3, 4) == {'x': 1}


def test_tacos_log_and_channel_gifts(db):
    db.connection.tacos_log.insert_one = MagicMock()
    db.track_tacos_log(1, 2, 3, 4, 't', 'r')
    assert db.connection.tacos_log.insert_one.called

    db.connection.twitch_tacos_gifts.find = MagicMock(return_value=[{'count': 2}, {'count': 3}])
    assert db.get_total_gifted_tacos_for_channel(1, '#foo') == 5

    db.connection.twitch_tacos_gifts.find = MagicMock(return_value=None)
    assert db.get_total_gifted_tacos_for_channel(1, '#foo') == 0

    db.connection.twitch_tacos_gifts.find = MagicMock(side_effect=RuntimeError('boom'))
    assert db.get_total_gifted_tacos_for_channel(1, '#foo') == 0

    db.connection.twitch_tacos_gifts.find = MagicMock(return_value=[{'count': 1}])
    assert db.get_total_gifted_tacos_to_user(1, '#foo', 'bob') == 1


def _args_for_signature(func):
    sig = inspect.signature(func)
    args = []
    for name, param in sig.parameters.items():
        if name == 'self':
            continue
        if 'guild' in name.lower() or name.endswith('Id') or 'user' in name.lower():
            args.append(1)
        elif name in ('channel', 'user'):
            args.append('#foo')
        elif name == 'timespan_seconds':
            args.append(3600)
        elif name == 'messageId' or 'message' in name:
            args.append(12)
        elif name == 'count' or name == 'vote':
            args.append(2)
        elif name == 'type' or name == 'reason':
            args.append('x')
        else:
            args.append(1)
    return args


def test_all_methods_open_and_exceptions(db):
    cls = TacosDatabase
    for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith('_'):
            continue
        src = inspect.getsource(func)
        m = re.search(r'self\.connection\.([a-zA-Z0-9_]+)\.([a-z_]+)\(', src)
        if not m:
            continue
        coll, op = m.group(1), m.group(2)

        # test open fallback
        db.client = None
        db.connection = None

        def opener():
            db.connection = MagicMock()
            setattr(db.connection, coll, MagicMock())
            getattr(db.connection, coll).configure_mock(**{op: MagicMock()})

        db.open = MagicMock(side_effect=opener)
        meth = getattr(db, name)
        args = _args_for_signature(meth)
        try:
            meth(*args)
        except Exception:
            pass
        assert db.open.called

        # test exception path -> underlying operation raises
        db.open.reset_mock()
        db.log.reset_mock()
        db.client = object()
        c = MagicMock()
        op_mock = MagicMock(side_effect=RuntimeError('boom'))
        setattr(c, op, op_mock)
        db.connection = MagicMock()
        setattr(db.connection, coll, c)

        try:
            result = getattr(db, name)(*args)
        except Exception:
            result = 'RAISED'

        # assert we logged or returned expected failure value for some functions
        if name in ('get_total_gifted_tacos', 'get_total_gifted_tacos_for_channel', 'get_total_gifted_tacos_to_user'):
            assert result == 0
        elif name == 'add_taco_gift':
            assert result is False
        elif name == 'get_tacos_count':
            assert result is None
        else:
            assert db.log.called
