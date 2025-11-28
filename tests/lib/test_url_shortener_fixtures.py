import json
from unittest.mock import MagicMock


def test_default_api_url_and_headers(mock_requests_post):
    # When constructed with only access_token, UrlShortener should use the default bitly-style API URL
    from bot.lib.UrlShortener import UrlShortener

    u = UrlShortener(access_token="xyz")

    # prepare response
    resp = MagicMock()
    resp.text = "ok"
    resp.json.return_value = {"short": "ok"}
    mock_requests_post.return_value = resp

    # call shorten and assert post url and headers
    out = u.shorten(long_url="https://example.com/path")
    assert out == {"short": "ok"}

    assert mock_requests_post.called
    call_args = mock_requests_post.call_args[0]
    assert call_args[0] == "https://api-ssl.bitly.com/v4/api/shorten"
    # headers should include the access token
    call_kwargs = mock_requests_post.call_args[1]
    assert call_kwargs["headers"]["X-ACCESS-TOKEN"] == "xyz"
    assert call_kwargs["headers"]["Content-Type"] == "application/json"


def test_shorten_prints_payload_and_response(url_shortener, mock_requests_post, capsys):
    # Using the shared url_shortener fixture and mock request to verify printed output
    resp = MagicMock()
    resp.text = "server-response"
    resp.json.return_value = {"ok": True}
    mock_requests_post.return_value = resp

    # call with two params and capture stdout
    r = url_shortener.shorten(a=1, b=2)
    assert r == {"ok": True}

    captured = capsys.readouterr()
    # UrlShortener is quiet now; no output should be present
    assert captured.out == ""
