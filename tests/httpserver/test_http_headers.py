from httpserver.HttpHeaders import HttpHeaders


def test_set_get_and_len_and_dict():
    h = HttpHeaders()
    returned = h.set('Content-Type', 'text/plain')
    assert returned is h
    assert h.get('content-type') == 'text/plain'
    assert h.get('missing', 'x') == 'x'
    assert len(h) == 1

    # dict-like representation returns first values
    d = h.__dict__()
    assert d == {'content-type': 'text/plain'}


def test_add_and_get_list_and_getitem():
    h = HttpHeaders()
    h.set('X-Test', 'one')
    h.add('X-Test', 'two')

    vals = h.get_list('x-test')
    assert vals == ['one', 'two']

    # __getitem__ returns raw list for that key
    assert h['x-test'] == ['one', 'two']


def test_from_dict_and_items_keys():
    h = HttpHeaders.from_dict({'A': '1', 'B': '2'})
    keys = list(h.keys())
    assert 'a' in keys and 'b' in keys

    # items yields pairs for each value
    items = list(h.items())
    assert ('a', '1') in items and ('b', '2') in items


def test_merge_headers_and_dict_list_values():
    base = HttpHeaders()
    base.set('X', 'v1')

    other = HttpHeaders()
    other.set('X', 'v2')
    other.set('Y', 'val')

    base.merge(other)
    assert base.get_list('x') == ['v1', 'v2']

    # merge with a dict that contains list values and scalars
    base.merge({'x': ['v3', 'v4'], 'z': 'single'})
    assert base.get_list('x') == ['v1', 'v2', 'v3', 'v4']
    assert base.get('z') == 'single'


def test_repr_contains_internal_structure():
    h = HttpHeaders()
    h.set('One', '1')
    r = repr(h)
    assert 'one' in r and '1' in r
from httpserver.HttpHeaders import HttpHeaders


def test_set_and_get_list_and_get_default_and_transform():
    headers = HttpHeaders()
    # set will lowercase key
    headers.set("Content-Type", "text/plain")
    assert headers.get_list("content-type") == ["text/plain"]
    # get returns first value with default
    assert headers.get("content-type") == "text/plain"
    assert headers.get("missing", default="xyz") == "xyz"
    # transform function applied to first value
    assert headers.get("content-type", transform=lambda s: s.upper()) == "TEXT/PLAIN"


def test_add_and_len_and_items_and_keys_and_getitem_and_repr():
    headers = HttpHeaders()
    headers.set("X-Count", "1")
    headers.add("X-Count", "2")
    headers.add("X-Count", "3")
    # len should equal number of values
    assert len(headers) == 3
    # items should yield all pairs
    items = list(headers.items())
    assert ("x-count", "1") in items
    assert ("x-count", "2") in items
    assert ("x-count", "3") in items
    # keys view contains lowered key
    ks = headers.keys()
    assert "x-count" in ks
    # getitem returns list of values
    assert headers["X-Count"] == ["1", "2", "3"]
    # repr contains the lowecase key
    assert "x-count" in repr(headers)


def test_from_dict_and___dict__():
    headers = HttpHeaders.from_dict({"Content-Length": "123", "X-Flag": "on"})
    # keys are lowered
    assert headers.get("content-length") == "123"
    assert headers.get("x-flag") == "on"
    # __dict__ returns first values map
    d = headers.__dict__()
    assert d["content-length"] == "123"
    assert d["x-flag"] == "on"


def test_merge_with_headers_and_dict_variants():
    # merge HttpHeaders
    a = HttpHeaders()
    a.set("X-A", "1")
    b = HttpHeaders()
    b.set("X-A", "2")
    b.set("X-B", "b")
    a.merge(b)
    assert a.get_list("X-A") == ["1", "2"]
    assert a.get("X-B") == "b"

    # merge dict with list values and single values
    c = HttpHeaders()
    c.set("X-C", "first")
    c.merge({"X-C": ["second", "third"], "X-D": "single"})
    # note: merge with a plain dict does not lowercase keys -- those values will
    # be available under the original key case in the internal mapping
    assert c.get_list("x-c") == ["first"]
    # internal storage contains the merged values under the raw dict key
    assert c._headers["X-C"] == ["second", "third"]
    # single appended
    assert c._headers["X-D"] == ["single"]


def test_keys_view_iter_and_items_are_generators():
    headers = HttpHeaders()
    headers.set("A", "x")
    headers.set("B", "y")
    # making sure items returns a generator that can be iterated multiple times
    first = list(headers.items())
    second = list(headers.items())
    assert first == second


def test_get_list_returns_none_for_missing_key():
    headers = HttpHeaders()
    assert headers.get_list("nope") is None
