import json
from unittest.mock import MagicMock, patch

import pytest

from bot.lib.UrlShortener import UrlShortener


@patch("bot.lib.UrlShortener.requests.post")
@patch("builtins.print")
def test_shorten_posts_payload_and_returns_json(mock_print, mock_post):
    # arrange
    token = "ak"
    u = UrlShortener(access_token=token)

    # prepare response
    resp = MagicMock()
    resp.text = "ok"
    resp.json.return_value = {"link": "http://short"}
    mock_post.return_value = resp

    # act
    result = u.shorten(long_url="http://example.com")

    # assert
    assert result == {"link": "http://short"}
    mock_post.assert_called_once()
    # requests.post is called with the url as the first positional arg
    call_args = mock_post.call_args[0]
    assert call_args[0].endswith("/api/shorten")
    # headers included
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["headers"]["X-ACCESS-TOKEN"] == token
    # data is json string of payload
    assert json.loads(call_kwargs["data"]) == {"long_url": "http://example.com"}


def test_init_trims_trailing_slash_and_enforce_https_ok():
    u = UrlShortener(access_token="abc", api_url="https://example.com/")
    assert u.api_url == "https://example.com"

    # enforce https is fine with https
    u2 = UrlShortener(access_token="abc", api_url="https://secure.local", enforce_https=True)
    assert u2.api_url == "https://secure.local"


def test_init_enforce_https_raises():
    with pytest.raises(Exception, match="API URL must be a secure URL"):
        UrlShortener(access_token="abc", api_url="http://notsecure", enforce_https=True)


def test_init_missing_api_url_raises():
    with pytest.raises(Exception, match="Missing required api_url argument"):
        UrlShortener(access_token="abc", api_url="")

    with pytest.raises(Exception, match="Missing required api_url argument"):
        UrlShortener(access_token="abc", api_url=None)


def test_init_missing_access_token_raises():
    # present but blank
    with pytest.raises(Exception, match="Missing required access_token argument"):
        UrlShortener(access_token="", api_url="https://example.com")

    with pytest.raises(Exception, match="Missing required access_token argument"):
        UrlShortener(access_token=None, api_url="https://example.com")


def test_init_non_secure_url_without_enforce_https_ok():
    # enforce_https defaults to False - non-secure API URL should be accepted
    u = UrlShortener(access_token="abc", api_url="http://example.local", enforce_https=False)
    assert u.api_url.startswith("http://")


@patch("bot.lib.UrlShortener.requests.post")
@patch("builtins.print")
def test_shorten_raises_when_response_json_errors(mock_print, mock_post):
    u = UrlShortener(access_token="at")

    resp = MagicMock()
    resp.text = "bad"

    def json_raises():
        raise ValueError("invalid json")

    resp.json.side_effect = json_raises
    mock_post.return_value = resp

    with pytest.raises(ValueError):
        u.shorten(long_url="http://example.com")


@patch("bot.lib.UrlShortener.requests.post")
@patch("builtins.print")
def test_shorten_payload_keys_used(mock_print, mock_post):
    u = UrlShortener(access_token="tok", api_url="https://myapi")
    resp = MagicMock()
    resp.text = "ok"
    resp.json.return_value = {"ok": True}
    mock_post.return_value = resp

    r = u.shorten(a=1, b=2)
    assert r == {"ok": True}
    # confirm both keys present in payload
    call_kwargs = mock_post.call_args[1]
    assert json.loads(call_kwargs["data"]) == {"a": 1, "b": 2}


def test_init_without_access_token_key_raises_attribute_error():
    # If the caller does not supply the access_token key at all, the implementation attempts
    # to read self.access_token later which raises AttributeError - test that behavior.
    with pytest.raises(AttributeError):
        UrlShortener(api_url="https://example.com")
