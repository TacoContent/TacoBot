from bot.lib.models.SimpleStatusResponse import SimpleStatusResponse


def test_simple_status_response():
    ss = SimpleStatusResponse("ok")
    assert ss.to_dict()["status"] == "ok"
