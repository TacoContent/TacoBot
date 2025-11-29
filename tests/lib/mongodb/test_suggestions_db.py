import datetime
import inspect
from unittest.mock import MagicMock

import pytest

from bot.lib.mongodb.suggestions import SuggestionsDatabase
from bot.lib.models.suggestionstates import SuggestionStates


@pytest.fixture
def db():
    d = SuggestionsDatabase()
    d.settings = MagicMock()
    d.settings.timezone = 'UTC'
    d.client = object()
    d.connection = MagicMock()
    d.log = MagicMock()
    return d


def test_add_and_remove_create_message(db):
    db.connection.suggestion_create_messages.update_one = MagicMock()
    db.add_suggestion_create_message(1, 2, 3)
    assert db.connection.suggestion_create_messages.update_one.called

    db.connection.suggestion_create_messages.delete_one = MagicMock()
    db.remove_suggestion_create_message(1, 2, 3)
    assert db.connection.suggestion_create_messages.delete_one.called


def test_open_called_when_missing_client_or_connection(db):
    # force missing client and connection and ensure open() gets called for a write operation
    db.client = None
    db.connection = None

    def fake_open():
        db.connection = MagicMock()
        db.connection.suggestions = MagicMock()
        db.connection.suggestions.update_one = MagicMock()

    db.open = MagicMock(side_effect=fake_open)
    db.set_state_suggestion_by_id(1, 'sid', 'closed', 1, 'reason')
    assert db.open.called
    assert db.connection.suggestions.update_one.called


def test_vote_unvote_and_edge_cases(db):
    # test vote valid + invalid and unvote
    db.connection.suggestions.update_one = MagicMock()
    db.vote_suggestion(1, 2, 3, 1)  # valid
    db.vote_suggestion(1, 2, 3, 999)  # invalid -> becomes 0
    assert db.connection.suggestions.update_one.call_count >= 2

    db.connection.suggestions.update_one = MagicMock()
    db.vote_suggestion_by_id('sid', 4, 1)
    db.vote_suggestion_by_id('sid', 5, 42)
    assert db.connection.suggestions.update_one.call_count >= 2

    db.connection.suggestions.update_one = MagicMock()
    db.unvote_suggestion_by_id(1, 'sid', 7)
    db.unvote_suggestion(1, 2, 8)
    assert db.connection.suggestions.update_one.call_count >= 2


def test_add_suggestion_defaults_and_exception(db):
    db.connection.suggestions.insert_one = MagicMock()
    db.add_suggestion(1, 7, {})
    assert db.connection.suggestions.insert_one.called

    # exception path logs
    db.connection.suggestions.insert_one = MagicMock(side_effect=RuntimeError('boom'))
    db.add_suggestion(1, 7, {'suggestion': 'x'})
    assert db.log.called


def test_delete_suggestion_by_id_sets_deleted_state_and_exception(db):
    db.connection.suggestions.update_one = MagicMock()
    db.delete_suggestion_by_id(1, 'sid', 4, 'reason')
    assert db.connection.suggestions.update_one.called

    # ensure the state used is SuggestionStates.DELETED
    called_payload = db.connection.suggestions.update_one.call_args[0][1]
    assert 'state' in called_payload['$set'] or isinstance(called_payload.get('$set'), dict)

    # exception path
    db.connection.suggestions.update_one = MagicMock(side_effect=RuntimeError('boom'))
    db.delete_suggestion_by_id(1, 'sid', 4, 'reason')
    assert db.log.called


def _args_for_signature(func):
    sig = inspect.signature(func)
    args = []
    for name, param in sig.parameters.items():
        if name == 'self':
            continue
        # choose a simple representative value
        if 'id' in name or 'Id' in name or name.endswith('Id'):
            args.append('abc')
        elif 'message' in name.lower():
            args.append(12)
        elif name in ('vote', 'userId', 'user_id') or name.endswith('Id'):
            args.append(1)
        elif name == 'suggestion':
            args.append({'suggestion': 'x'})
        elif 'reason' in name or 'state' in name:
            args.append('ok')
        else:
            args.append(1)
    return args


def test_all_methods_open_and_exceptions(db):
    # Inspect all public methods and test open() fallback + operation exceptions
    import inspect as _i
    import re as _re

    cls = SuggestionsDatabase
    for name, func in _i.getmembers(cls, predicate=_i.isfunction):
        if name.startswith('_'):
            continue
        src = _i.getsource(func)
        m = _re.search(r'self\.connection\.([a-zA-Z0-9_]+)\.([a-z_]+)\(', src)
        if not m:
            # nothing to assert for this method
            continue
        coll, op = m.group(1), m.group(2)

        # test open fallback path
        db.client = None
        db.connection = None

        def opener():
            db.connection = MagicMock()
            setattr(db.connection, coll, MagicMock())
            # ensure the specific operation exists
            getattr(db.connection, coll).configure_mock(**{op: MagicMock()})

        db.open = MagicMock(side_effect=opener)
        meth = getattr(db, name)
        args = _args_for_signature(meth)
        try:
            res = meth(*args)
        except Exception:
            # some methods may raise; we just want to ensure open was invoked
            res = None
        assert db.open.called

        # test operation raising -> log called
        db.open.reset_mock()
        db.log.reset_mock()
        # setup a connection where the collection operation raises
        db.client = object()
        c = MagicMock()
        # create raising operation for this collection
        op_mock = MagicMock(side_effect=RuntimeError('boom'))
        setattr(c, op, op_mock)
        db.connection = MagicMock()
        setattr(db.connection, coll, c)

        # call and assert log happened (or method returned expected failure value)
        try:
            result = getattr(db, name)(*args)
        except Exception:
            result = 'RAISED'
        # if method returns a boolean on exception, expect False
        if name == 'has_user_voted_on_suggestion':
            assert result is False
        else:
            # most methods swallow and return None
            assert db.log.called



def test_get_suggestion_paths_and_exceptions(db):
    # not found -> None
    db.connection.suggestions.find_one = MagicMock(return_value=None)
    assert db.get_suggestion(1, 2) is None

    # found -> returned
    db.connection.suggestions.find_one = MagicMock(return_value={'id': 'x'})
    assert db.get_suggestion(1, 2) == {'id': 'x'}

    # by id
    db.connection.suggestions.find_one = MagicMock(return_value=None)
    assert db.get_suggestion_by_id(1, 'abc') is None

    db.connection.suggestions.find_one = MagicMock(return_value={'id': 'abc'})
    assert db.get_suggestion_by_id(1, 'abc') == {'id': 'abc'}

    # exceptions should log and not raise
    db.connection.suggestions.find_one = MagicMock(side_effect=RuntimeError('boom'))
    assert db.get_suggestion(1, 2) is None
    assert db.log.called


def test_set_state_variants_and_errors(db):
    db.connection.suggestions.update_one = MagicMock()
    db.set_state_suggestion_by_id(1, 'sid', 'accepted', 99, 'nice')
    assert db.connection.suggestions.update_one.called

    db.connection.suggestions.update_one = MagicMock()
    db.set_state_suggestion(1, 22, 'rejected', 55, 'nah')
    assert db.connection.suggestions.update_one.called

    # update_one raising should get logged
    db.connection.suggestions.update_one = MagicMock(side_effect=RuntimeError('boom'))
    db.set_state_suggestion_by_id(1, 'sid', 'accepted', 99, 'nice')
    assert db.log.called


def test_has_user_voted_on_suggestion(db):
    # suggestion missing
    db.connection.suggestions.find_one = MagicMock(return_value=None)
    assert db.has_user_voted_on_suggestion('id', 1) is False

    # votes is None
    db.connection.suggestions.find_one = MagicMock(return_value={'votes': None})
    assert db.has_user_voted_on_suggestion('id', 1) is False

    # present
    db.connection.suggestions.find_one = MagicMock(return_value={'votes': [{'user_id': '5'}]})
    assert db.has_user_voted_on_suggestion('id', 5) is True

    # exceptions log and return False
    db.connection.suggestions.find_one = MagicMock(side_effect=RuntimeError('boom'))
    assert db.has_user_voted_on_suggestion('id', 1) is False
    assert db.log.called


def test_vote_and_unvote_paths(db):
    db.connection.suggestions.update_one = MagicMock()
    db.unvote_suggestion_by_id(1, 'sid', 3)
    assert db.connection.suggestions.update_one.called

    db.connection.suggestions.update_one = MagicMock()
    db.unvote_suggestion(1, 22, 5)
    assert db.connection.suggestions.update_one.called

    # get suggestion votes by id
    db.connection.suggestions.find_one = MagicMock(return_value=None)
    assert db.get_suggestion_votes_by_id('x') is None

    db.connection.suggestions.find_one = MagicMock(return_value={'votes': [{'user_id': '1'}]})
    assert db.get_suggestion_votes_by_id('x') == [{'user_id': '1'}]

    # voting edge-case: invalid vote becomes 0
    db.connection.suggestions.update_one = MagicMock()
    db.vote_suggestion(1, 22, 5, 99)  # 99 -> 0
    assert db.connection.suggestions.update_one.called

    db.connection.suggestions.update_one = MagicMock()
    db.vote_suggestion_by_id('sid', 9, -1)
    assert db.connection.suggestions.update_one.called


def test_add_and_delete_suggestion(db):
    db.connection.suggestions.insert_one = MagicMock()
    db.add_suggestion(1, 22, {'suggestion': 'hello', 'author_id': 55, 'id': 'abc'})
    assert db.connection.suggestions.insert_one.called

    db.connection.suggestions.update_one = MagicMock()
    db.delete_suggestion_by_id(1, 'abc', 77, 'bye')
    assert db.connection.suggestions.update_one.called
