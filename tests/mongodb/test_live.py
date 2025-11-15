from unittest.mock import MagicMock, patch

from bot.lib.mongodb.live import LiveDatabase


@patch("bot.lib.mongodb.live.utils.to_timestamp", return_value=999999)
def test_track_live_activity_inserts_payload(mock_to_ts):
    db = LiveDatabase()

    # patch open to set connection
    db.client = MagicMock()
    db.connection = MagicMock()

    db.track_live_activity(123, 456, True, "twitch", "http://url")

    # ensure insert_one called with correct payload
    assert db.connection.live_activity.insert_one.called
    payload = db.connection.live_activity.insert_one.call_args[0][0]
    assert payload["guild_id"] == "123"
    assert payload["user_id"] == "456"
    assert payload["status"] == "ONLINE"
    assert payload["platform"] == "TWITCH"
    assert payload["url"] == "http://url"
    assert payload["timestamp"] == 999999


def test_track_live_raises_on_missing_required():
    db = LiveDatabase()

    # track_live logs and returns on validation errors (method catches exceptions)
    def fake_open():
        db.client = MagicMock()
        db.connection = MagicMock()

    db.open = fake_open
    db.open()  # Ensure db.open is called before using db.connection
    db.log = MagicMock()

    db.track_live(1, 2, None)
    assert db.log.called

    db.log.reset_mock()
    db.track_live(1, None, "twitch")
    assert db.log.called

    db.log.reset_mock()
    db.track_live(None, 2, "twitch")
    assert db.log.called


@patch("bot.lib.mongodb.live.utils.to_timestamp", return_value=424242)
def test_track_live_updates_and_upserts(mock_to_ts):
    db = LiveDatabase()

    def fake_open():
        db.client = MagicMock()
        db.connection = MagicMock()

    db.open = fake_open
    db.open()  # Ensure db.open is called before using db.connection

    db.track_live(10, 20, "YouTube", channelId=30, messageId=40, url="http://x")

    assert db.connection.live_tracked.update_one.called
    args = db.connection.live_tracked.update_one.call_args[0]
    # filter
    expected_filter = {"guild_id": "10", "user_id": "20", "platform": "YOUTUBE"}
    assert args[0] == expected_filter

    # data set
    set_doc = db.connection.live_tracked.update_one.call_args[0][1]["$set"]
    assert set_doc["channel_id"] == "30"
    assert set_doc["message_id"] == "40"
    assert set_doc["platform"] == "YOUTUBE"
    assert set_doc["url"] == "http://x"
    assert set_doc["timestamp"] == 424242


def test_get_tracked_live_and_user_and_by_url_return_values():
    db = LiveDatabase()

    def fake_open():
        db.client = MagicMock()
        db.connection = MagicMock()

    db.open = fake_open
    db.open()  # Ensure db.open is called before using db.connection
    # find returns a list-like
    db.connection.live_tracked.find.return_value = [1, 2, 3]

    vals = db.get_tracked_live(1, 2, "TWITCH")
    assert vals == [1, 2, 3]

    db.connection.live_tracked.find.return_value = "cursor"
    c = db.get_tracked_live_by_url(1, "http://x")
    assert c == "cursor"

    db.connection.live_tracked.find.return_value = ["a"]
    u = db.get_tracked_live_by_user(1, 2)
    assert u == ["a"]


def test_untrack_live_calls_delete_many():
    db = LiveDatabase()

    def fake_open():
        db.client = MagicMock()
        db.connection = MagicMock()

    db.open = fake_open
    db.open()  # Ensure db.open is called before using db.connection
    db.untrack_live(1, 2, "twitch")

    db.connection.live_tracked.delete_many.assert_called_once()
    filt = db.connection.live_tracked.delete_many.call_args[0][0]
    assert filt["guild_id"] == "1"
    assert filt["user_id"] == "2"
    assert filt["platform"] == "TWITCH"


def test_exception_handling_calls_log_on_error(monkeypatch):
    db = LiveDatabase()

    # open raises - ensure log called
    def fake_open_raise():
        raise RuntimeError("boom")

    db.open = fake_open_raise
    # make sure log is replaced by a MagicMock
    db.log = MagicMock()

    # track_live_activity should call log when open raises
    db.track_live_activity(1, 2, True, "twitch", "url")
    assert db.log.called

    # track_live should also call log on error
    db.log.reset_mock()
    db.track_live(1, 2, "twitch")
    assert db.log.called

    # get_tracked_live should call log
    db.log.reset_mock()
    res = db.get_tracked_live(1, 2, "twitch")
    assert db.log.called

    # get_tracked_live_by_url should call log
    db.log.reset_mock()
    res = db.get_tracked_live_by_url(1, "u")
    assert db.log.called

    # get_tracked_live_by_user should call log
    db.log.reset_mock()
    res = db.get_tracked_live_by_user(1, 2)
    assert db.log.called

    # untrack_live should call log
    db.log.reset_mock()
    db.untrack_live(1, 2, "twitch")
    assert db.log.called
