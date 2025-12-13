import datetime
import types

from bot.lib.enums.system_actions import SystemActions
from bot.lib.models.DiscordUser import DiscordUser
from bot.lib.models.triviaquestion import TriviaQuestion
from bot.lib.mongodb.tracking import TrackingDatabase


class FakeColl:
    def __init__(self):
        self.insert_calls = []
        self.update_calls = []

    def insert_one(self, payload):
        self.insert_calls.append(payload)

    def update_one(self, q, u=None, upsert=False):
        self.update_calls.append({'q': q, 'u': u, 'upsert': upsert})

    def find_one(self, q):
        return None

    def find(self, q):
        return iter([])


def make_open_stub(db, mapping):
    """Return a stub that will set client and connection to a SimpleNamespace with given mapping."""

    def _open():
        db.client = object()
        # ensure logs exists so insert_log doesn't fail when an exception path hits
        if 'logs' not in mapping:
            mapping['logs'] = FakeColl()
        db.connection = types.SimpleNamespace(**mapping)

    return _open


def test_open_path_for_command_usage_and_first_message_and_message_and_is_first_today():
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"

    fake_cmd = FakeColl()
    fake_fm = FakeColl()
    fake_msg = FakeColl()
    mapping = {"commands_usage": fake_cmd, "first_message": fake_fm, "messages": fake_msg}

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, mapping)

    # exercise track_command_usage open() branch
    db.track_command_usage(1, None, 3, "c")
    assert fake_cmd.insert_calls

    # exercise track_first_message open() branch
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, mapping)
    db.track_first_message(1, 2, 3, 4)
    assert fake_fm.update_calls

    # exercise track_message open() branch for insert
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, mapping)
    db.track_message(1, 2, 3, 4)
    assert fake_msg.insert_calls

    # is_first_message_today open() branch -> returns True when nothing present
    db.client = None
    db.connection = None
    # set first_message.find_one to return None by making a fake coll without entries
    class Fm:
        def find_one(self, q):
            return None

    db.open = make_open_stub(db, {"first_message": Fm()})
    assert db.is_first_message_today(1, 2) is True


def test_open_path_for_discord_user_and_guild_and_trivia_and_system_action_and_introductions_and_free_game():
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"

    fake_users = FakeColl()
    fake_guilds = FakeColl()
    fake_trivia = FakeColl()
    fake_sys = FakeColl()
    fake_intros = FakeColl()
    fake_free = FakeColl()

    mapping = {
        "users": fake_users,
        "guilds": fake_guilds,
        "trivia_questions": fake_trivia,
        "system_actions": fake_sys,
        "introductions": fake_intros,
        "track_free_game_keys": fake_free,
    }

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, mapping)

    # discord user update (user.to_dict must exist)
    u = DiscordUser({"id": "100", "guild_id": "5", "name": "z"})
    db.track_discord_user(u)
    assert fake_users.update_calls

    # track_guild
    class G:
        def __init__(self):
            self.id = 77
            self.name = "G"
            self.owner_id = 9
            self.created_at = datetime.datetime.now(tz=datetime.timezone.utc)
            self.vanity_url = None
            self.vanity_url_code = None
            self.icon = None

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {"guilds": fake_guilds})
    db.track_guild(G())
    assert fake_guilds.update_calls

    # trivia insert
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {"trivia_questions": fake_trivia})
    tq = TriviaQuestion(1, 2, 3, 4, 'q', 'a', ['b'], 'cat', 1)
    db.track_trivia_question(tq)
    assert fake_trivia.insert_calls

    # system action
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {"system_actions": fake_sys})
    db.track_system_action(1, SystemActions.NEW_ACCOUNT_KICK, data={'a': 'b'})
    assert fake_sys.insert_calls

    # introductions
    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {"introductions": fake_intros})
    db.track_user_introduction(1, 2, 3, 4, False)
    assert fake_intros.update_calls

    # track_free_game_key: need timezone on settings
    db.client = None
    db.connection = None
    db.settings.timezone = 'UTC'
    db.open = make_open_stub(db, {"track_free_game_keys": fake_free})
    db.track_free_game_key(1, 2, 3, 4)
    assert fake_free.update_calls


def test_open_path_for_photo_and_join_leave_and_shift_code():
    db = TrackingDatabase()
    db.db_url = "mongodb://ok"

    fake_photo = FakeColl()
    fake_join = FakeColl()
    fake_shift = FakeColl()

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {"photo_posts": fake_photo})
    db.track_photo_post(1, 2, 3, 4, 'm', 'img', 'chn')
    assert fake_photo.insert_calls

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {"user_join_leave": fake_join})
    db.track_user_join_leave(1, 2, True)
    assert fake_join.insert_calls

    db.client = None
    db.connection = None
    db.open = make_open_stub(db, {"shift_codes": fake_shift})
    db.track_shift_code(1, 2, 3, ' code  ')
    assert fake_shift.update_calls
