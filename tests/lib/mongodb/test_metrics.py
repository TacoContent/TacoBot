import inspect
import re
from unittest.mock import MagicMock

import pytest

from bot.lib.mongodb.metrics import MetricsDatabase


class FakeCollection:
    def __init__(self, result=None, raises=False, method='aggregate'):
        self._result = result if result is not None else [{'ok': True}]
        self._raises = raises
        self._method = method

        def agg(*a, **k):
            if self._raises:
                raise RuntimeError('boom')
            return self._result

        def find(*a, **k):
            if self._raises:
                raise RuntimeError('boom')
            return self._result

        self.aggregate = MagicMock(side_effect=agg)
        self.find = MagicMock(side_effect=find)


class FakeConnection:
    def __init__(self, result=None, raises_for=None, find_raises_for=None):
        self._result = result if result is not None else [{'ok': True}]
        self._raises_for = set(raises_for or [])
        self._find_raises_for = set(find_raises_for or [])

    def __getattr__(self, name: str):
        raises = name in self._raises_for
        find_raises = name in self._find_raises_for
        # If both are true, prefer raising on aggregate
        obj = FakeCollection(result=self._result, raises=raises or find_raises)
        setattr(self, name, obj)
        return obj


@pytest.fixture
def db():
    d = MetricsDatabase()
    d.settings = MagicMock()
    d.settings.timezone = 'UTC'
    d.client = object()
    d.connection = FakeConnection()
    d.log = MagicMock()
    return d


def _get_collection_name(method):
    # inspect source to see which collection it references (first match)
    src = inspect.getsource(method)
    m = re.search(r'self\.connection\.([a-zA-Z_0-9]+)\.', src)
    if m:
        return m.group(1)
    # fallback to None
    return None


@pytest.mark.parametrize('method_name', [m for m in dir(MetricsDatabase) if m.startswith('get_')])
def test_get_methods_happy_path(db, method_name):
    # ensure every get_* returns a truthy value when connection is present
    meth = getattr(db, method_name)

    # call the method (no connection None) and assert truthy / not raising
    result = meth()
    assert result is not None


@pytest.mark.parametrize('method_name', [m for m in dir(MetricsDatabase) if m.startswith('get_')])
def test_get_methods_open_when_no_connection(db, method_name):
    # connection missing -> open() should be called and method should still return something
    db.connection = None

    # make the open method create a fake connection
    def fake_open():
        db.connection = FakeConnection(result=[{'created': True}])

    db.open = MagicMock(side_effect=fake_open)

    meth = getattr(db, method_name)

    # calling should not raise and open should have been invoked
    val = meth()
    assert db.open.called
    # some methods return lists, iterators, or None on exception — for a normal path we expect non-None
    assert val is not None


@pytest.mark.parametrize('method_name', [m for m in dir(MetricsDatabase) if m.startswith('get_')])
def test_get_methods_exception_logs_and_return(db, method_name):
    # find the collection referenced and make its aggregate/find raise
    meth = getattr(MetricsDatabase, method_name)
    coll = _get_collection_name(meth)

    # create a connection that will raise on that collection
    if coll:
        # decide whether the method uses find() (e.g., get_guilds) by checking for '.find('
        src = inspect.getsource(meth)
        uses_find = '.find(' in src
        if uses_find:
            db.connection = FakeConnection(result=[], find_raises_for=[coll])
        else:
            db.connection = FakeConnection(result=[], raises_for=[coll])
    else:
        # defensive: if we can't find a collection, force open to raise
        db.connection = FakeConnection(result=[], raises_for=['unknown_collection'])

    # call method
    try:
        res = getattr(db, method_name)()
    except Exception:
        # some methods may re-raise intentionally (none in metrics expected to re-raise)
        res = 'RAISED'

    # methods generally swallow exceptions and return None OR empty list for trivia questions
    if method_name == 'get_trivia_questions':
        assert res == []
    else:
        assert res is None

    assert db.log.called
