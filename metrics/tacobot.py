import inspect
import os
import socket
import time
import traceback

from bot.lib import logger
from bot.lib.enums.loglevel import LogLevel
from bot.lib.enums.permissions import TacoPermissions
from bot.lib.mongodb.metrics import MetricsDatabase
from bot.lib.settings import Settings
from bot.lib.utils import dict_get
from prometheus_client import Gauge


class TacoBotMetrics:
    def __init__(self, config):
        # get the class name
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]

        self.settings = Settings()

        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG
        self.log = logger.Log(log_level)

        self.namespace = "tacobot"
        self.polling_interval_seconds = config.metrics["pollingInterval"]
        self.config = config
        labels = ["guild_id"]

        user_labels = ["guild_id", "user_id", "username"]
        photo_post_labels = ["guild_id", "user_id", "username", "channel"]
        live_labels = ["guild_id", "user_id", "username", "platform"]

        # merge labels and config labels
        # labels = labels + [x['name'] for x in self.config.labels]
        self.db = MetricsDatabase()

        self.sum_tacos = Gauge(
            namespace=self.namespace, name="tacos", documentation="The number of tacos give to users", labelnames=labels
        )

        self.sum_taco_gifts = Gauge(
            namespace=self.namespace,
            name="taco_gifts",
            documentation="The number of tacos gifted to users",
            labelnames=labels,
        )

        self.sum_taco_reactions = Gauge(
            namespace=self.namespace,
            name="taco_reactions",
            documentation="The number of tacos given to users via reactions",
            labelnames=labels,
        )

        self.sum_live_now = Gauge(
            namespace=self.namespace,
            name="live_now",
            documentation="The number of people currently live",
            labelnames=labels,
        )

        self.sum_twitch_channels = Gauge(
            namespace=self.namespace,
            name="twitch_channels",
            documentation="The number of twitch channels the bot is watching",
            labelnames=labels,
        )

        self.sum_twitch_tacos = Gauge(
            namespace=self.namespace,
            name="twitch_tacos",
            documentation="The number of tacos given to twitch users",
            labelnames=labels,
        )

        self.sum_twitch_linked_accounts = Gauge(
            namespace=self.namespace,
            name="twitch_linked_accounts",
            documentation="The number of twitch accounts linked to discord accounts",
            labelnames=[],
        )

        self.sum_tqotd_questions = Gauge(
            namespace=self.namespace,
            name="tqotd",
            documentation="The number of questions in the TQOTD database",
            labelnames=labels,
        )

        self.sum_tqotd_answers = Gauge(
            namespace=self.namespace,
            name="tqotd_answers",
            documentation="The number of answers in the TQOTD database",
            labelnames=labels,
        )

        self.sum_invited_users = Gauge(
            namespace=self.namespace,
            name="invited_users",
            documentation="The number of users invited to the server",
            labelnames=labels,
        )

        self.sum_live_platform = Gauge(
            namespace=self.namespace,
            name="live_platform",
            documentation="The number of users that have gone live on a platform",
            labelnames=["guild_id", "platform"],
        )

        self.sum_wdyctw = Gauge(
            namespace=self.namespace,
            name="wdyctw_questions",
            documentation="The number of questions in the WDYCTW database",
            labelnames=labels,
        )

        self.sum_wdyctw_answers = Gauge(
            namespace=self.namespace,
            name="wdyctw_answers",
            documentation="The number of answers in the WDYCTW database",
            labelnames=labels,
        )

        self.sum_techthurs = Gauge(
            namespace=self.namespace,
            name="techthurs",
            documentation="The number of questions in the TechThurs database",
            labelnames=labels,
        )

        self.sum_techthurs_answers = Gauge(
            namespace=self.namespace,
            name="techthurs_answers",
            documentation="The number of answers in the TechThurs database",
            labelnames=labels,
        )

        self.sum_mentalmondays = Gauge(
            namespace=self.namespace,
            name="mentalmondays",
            documentation="The number of questions in the MentalMondays database",
            labelnames=labels,
        )

        self.sum_mentalmondays_answers = Gauge(
            namespace=self.namespace,
            name="mentalmondays_answers",
            documentation="The number of answers in the MentalMondays database",
            labelnames=labels,
        )

        self.sum_tacotuesday = Gauge(
            namespace=self.namespace,
            name="tacotuesday",
            documentation="The number of featured posts for TacoTuesday",
            labelnames=labels,
        )

        self.sum_tacotuesday_answers = Gauge(
            namespace=self.namespace,
            name="tacotuesday_answers",
            documentation="The number of interactions in the TacoTuesday database",
            labelnames=labels,
        )

        self.sum_game_keys_available = Gauge(
            namespace=self.namespace,
            name="game_keys_available",
            documentation="The number of game keys available",
            labelnames=["guild_id"],
        )

        self.sum_game_keys_claimed = Gauge(
            namespace=self.namespace,
            name="game_keys_redeemed",
            documentation="The number of game keys claimed",
            labelnames=["guild_id"],
        )

        self.sum_user_game_keys_claimed = Gauge(
            namespace=self.namespace,
            name="user_game_keys_redeemed",
            documentation="The number of game keys claimed by a user",
            labelnames=["guild_id", "user_id", "username"],
        )

        self.sum_user_game_keys_submitted = Gauge(
            namespace=self.namespace,
            name="user_game_keys_submitted",
            documentation="The number of game keys submitted by a user",
            labelnames=["guild_id", "user_id", "username"],
        )

        self.sum_minecraft_whitelist = Gauge(
            namespace=self.namespace,
            name="minecraft_whitelist",
            documentation="The number of users on the minecraft whitelist",
            labelnames=["guild_id"],
        )

        self.sum_logs = Gauge(
            namespace=self.namespace, name="logs", documentation="The number of logs", labelnames=["guild_id", "level"]
        )

        self.sum_stream_team_requests = Gauge(
            namespace=self.namespace,
            name="team_requests",
            documentation="The number of stream team requests",
            labelnames=labels,
        )

        self.sum_birthdays = Gauge(
            namespace=self.namespace, name="birthdays", documentation="The number of birthdays", labelnames=labels
        )

        self.sum_first_messages = Gauge(
            namespace=self.namespace,
            name="first_messages_today",
            documentation="The number of first messages today",
            labelnames=labels,
        )

        self.known_users = Gauge(
            namespace=self.namespace,
            name="known_users",
            documentation="The number of known users",
            labelnames=["guild_id", "type"],
        )

        self.top_messages = Gauge(
            namespace=self.namespace,
            name="messages",
            documentation="The number of top messages",
            labelnames=user_labels,
        )

        self.top_gifters = Gauge(
            namespace=self.namespace, name="gifters", documentation="The number of top gifters", labelnames=user_labels
        )

        self.top_reactors = Gauge(
            namespace=self.namespace,
            name="reactors",
            documentation="The number of top reactors",
            labelnames=user_labels,
        )

        self.top_tacos = Gauge(
            namespace=self.namespace, name="top_tacos", documentation="The number of top tacos", labelnames=user_labels
        )

        self.taco_logs = Gauge(
            namespace=self.namespace,
            name="taco_logs",
            documentation="The number of taco logs",
            labelnames=["guild_id", "type"],
        )

        self.top_live_activity = Gauge(
            namespace=self.namespace,
            name="live_activity",
            documentation="The number of top live activity",
            labelnames=live_labels,
        )

        self.suggestions = Gauge(
            namespace=self.namespace,
            name="suggestions",
            documentation="The number of suggestions",
            labelnames=["guild_id", "status"],
        )

        self.user_join_leave = Gauge(
            namespace=self.namespace,
            name="user_join_leave",
            documentation="The number of users that have joined or left",
            labelnames=["guild_id", "action"],
        )

        self.photo_posts = Gauge(
            namespace=self.namespace,
            name="photo_posts",
            documentation="The number of photo posts",
            labelnames=photo_post_labels,
        )

        self.guilds = Gauge(
            namespace=self.namespace,
            name="guilds",
            documentation="The number of guilds",
            labelnames=["guild_id", "name"],
        )

        # result is either correct or incorrect
        trivia_labels = ["guild_id", "difficulty", "category", "starter_id", "starter_name"]
        self.trivia_questions = Gauge(
            namespace=self.namespace,
            name="trivia_questions",
            documentation="The number of trivia questions",
            labelnames=trivia_labels,
        )

        self.trivia_answers = Gauge(
            namespace=self.namespace,
            name="trivia_answers",
            documentation="The number of trivia answers",
            labelnames=["guild_id", "user_id", "username", "state"],
        )

        self.invites = Gauge(
            namespace=self.namespace,
            name="invites",
            documentation="The number of invites",
            labelnames=["guild_id", "user_id", "username"],
        )

        self.system_actions = Gauge(
            namespace=self.namespace,
            name="system_actions",
            documentation="The number of system actions",
            labelnames=["guild_id", "action"],
        )

        self.user_status = Gauge(
            namespace=self.namespace,
            name="user_status",
            documentation="The number of users with a status",
            labelnames=["guild_id", "status"],
        )

        self.introductions = Gauge(
            namespace=self.namespace,
            name="introductions",
            documentation="The number of introductions",
            labelnames=["guild_id", "approved"],
        )

        self.twitch_stream_avatar_duel_winners = Gauge(
            namespace=self.namespace,
            name="twitch_stream_avatar_duel_winners",
            documentation="The number of twitch stream avatar duel winners",
            labelnames=["guild_id", "user_id", "username", "channel", "channel_user_id"],
        )

        self.free_game_keys = Gauge(
            namespace=self.namespace,
            name="free_game_keys",
            documentation="The number of free game keys",
            labelnames=["state"],
        )

        self.permission_count = Gauge(
            namespace=self.namespace,
            name="permission",
            documentation="The number of permission counts",
            labelnames=["guild_id", "permission"],
        )

        self.healthy = Gauge(
            namespace=self.namespace, name="healthy", documentation="The health of the bot", labelnames=[]
        )

        self.build_info = Gauge(
            namespace=self.namespace,
            name="build_info",
            documentation="A metric with a constant '1' value labeled with version",
            labelnames=["version", "ref", "build_date", "sha"],
        )

        self.errors = Gauge(
            namespace=self.namespace,
            name="exporter_errors",
            documentation="The number of errors encountered",
            labelnames=["source"],
        )

        ver = dict_get(os.environ, "APP_VERSION", "1.0.0-snapshot")
        ref = dict_get(os.environ, "APP_BUILD_REF", "unknown")
        build_date = dict_get(os.environ, "APP_BUILD_DATE", "unknown")
        sha = dict_get(os.environ, "APP_BUILD_SHA", "unknown")
        self.build_info.labels(version=ver, ref=ref, build_date=build_date, sha=sha).set(1)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Metrics initialized")

    def check_health(self):
        """Check the health of the bot"""
        _method = inspect.stack()[1][3]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.settimeout(10)
                    s.connect(("127.0.0.1", 40404))
                    data = s.recv(1024)
                except (ConnectionError, socket.timeout, ConnectionRefusedError):
                    data = b""

            self.healthy.set(1 if data == b"healthy" else 0)
            self.errors.labels(source="healthy").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.healthy.set(0)
            self.errors.labels(source="healthy").set(1)

    def run_metrics_loop(self):
        """Metrics fetching loop"""
        _method = inspect.stack()[1][3]
        try:
            while True:
                self.log.info(0, f"{self._module}.{self._class}.{_method}", "Begin metrics fetch")
                self.fetch()
                self.log.info(0, f"{self._module}.{self._class}.{_method}", "End metrics fetch")
                self.log.debug(
                    0,
                    f"{self._module}.{self._class}.{_method}",
                    f"Sleeping for {self.polling_interval_seconds} seconds",
                )
                time.sleep(self.polling_interval_seconds)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

    def fetch(self):
        """Fetch metrics from the database"""
        _method = inspect.stack()[1][3]

        self.check_health()

        known_guilds = []
        self.db.open()
        try:
            q_guilds = self.db.get_guilds() or []
            for row in q_guilds:
                known_guilds.append(row['guild_id'])
                self.guilds.labels(guild_id=row['guild_id'], name=row['name']).set(1)
            self.errors.labels(source="guilds").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="guilds").set(1)

        try:
            q_all_tacos = self.db.get_sum_all_tacos() or []
            for row in q_all_tacos:
                self.sum_tacos.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="tacos").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="tacos").set(1)

        try:
            q_all_gift_tacos = self.db.get_sum_all_gift_tacos() or []
            for row in q_all_gift_tacos:
                self.sum_taco_gifts.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="gift_tacos").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="gift_tacos").set(1)

        try:
            q_all_reaction_tacos = self.db.get_sum_all_taco_reactions() or []
            for row in q_all_reaction_tacos:
                self.sum_taco_reactions.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="reaction_tacos").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="reaction_tacos").set(1)

        try:
            q_live_now = self.db.get_live_now_count() or []
            for row in q_live_now:
                self.sum_live_now.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="live_now").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="live_now").set(1)

        try:
            q_twitch_channels = self.db.get_twitch_channel_bot_count() or []
            for row in q_twitch_channels:
                self.sum_twitch_channels.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="twitch_channels").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="twitch_channels").set(1)

        try:
            q_all_twitch_tacos = self.db.get_sum_all_twitch_tacos() or []
            for row in q_all_twitch_tacos:
                self.sum_twitch_tacos.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="twitch_tacos").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="twitch_tacos").set(1)

        try:
            q_twitch_linked_accounts = self.db.get_twitch_linked_accounts_count() or []
            for row in q_twitch_linked_accounts:
                self.sum_twitch_linked_accounts.set(row['total'])
            self.errors.labels(source="twitch_linked_accounts").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="twitch_linked_accounts").set(1)

        try:
            q_tqotd_questions = self.db.get_tqotd_questions_count() or []
            for row in q_tqotd_questions:
                self.sum_tqotd_questions.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="tqotd_questions").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="tqotd").set(1)

        try:
            q_tqotd_answers = self.db.get_tqotd_answers_count() or []
            for row in q_tqotd_answers:
                self.sum_tqotd_answers.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="tqotd_answers").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="tqotd_answers").set(1)

        try:
            q_invited_users = self.db.get_invited_users_count() or []
            for row in q_invited_users:
                self.sum_invited_users.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="invited_users").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="invited_users").set(1)

        try:
            q_live_platform = self.db.get_sum_live_by_platform() or []
            for row in q_live_platform:
                self.sum_live_platform.labels(guild_id=row['_id']['guild_id'], platform=row['_id']['platform']).set(
                    row['total']
                )
            self.errors.labels(source="live_platform").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="live_platform").set(1)

        try:
            q_wdyctw = self.db.get_wdyctw_questions_count() or []
            for row in q_wdyctw:
                self.sum_wdyctw.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="wdyctw").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="wdyctw").set(1)

        try:
            q_wdyctw_answers = self.db.get_wdyctw_answers_count() or []
            for row in q_wdyctw_answers:
                self.sum_wdyctw_answers.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="wdyctw_answers").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="wdyctw_answers").set(1)

        try:
            q_techthurs = self.db.get_techthurs_questions_count() or []
            for row in q_techthurs:
                self.sum_techthurs.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="techthurs").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="techthurs").set(1)

        try:
            q_techthurs_answers = self.db.get_techthurs_answers_count() or []
            for row in q_techthurs_answers:
                self.sum_techthurs_answers.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="techthurs_answers").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="techthurs_answers").set(1)

        try:
            q_mentalmondays = self.db.get_mentalmondays_questions_count() or []
            for row in q_mentalmondays:
                self.sum_mentalmondays.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="mentalmondays").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="mentalmondays").set(1)

        try:
            q_mentalmondays_answers = self.db.get_mentalmondays_answers_count() or []
            for row in q_mentalmondays_answers:
                self.sum_mentalmondays_answers.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="mentalmondays_answers").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="mentalmondays_answers").set(1)

        try:
            q_tacotuesday = self.db.get_tacotuesday_questions_count() or []
            for row in q_tacotuesday:
                self.sum_tacotuesday.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="tacotuesday").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="tacotuesday").set(1)

        try:
            q_tacotuesday_answers = self.db.get_tacotuesday_answers_count() or []
            for row in q_tacotuesday_answers:
                self.sum_tacotuesday_answers.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="tacotuesday_answers").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="tacotuesday_answers").set(1)

        try:
            q_game_keys_available = self.db.get_game_keys_available_count() or []
            for row in q_game_keys_available:
                self.sum_game_keys_available.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="game_keys_available").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="game_keys_available").set(1)

        try:
            q_game_keys_claimed = self.db.get_game_keys_redeemed_count() or []
            for row in q_game_keys_claimed:
                self.sum_game_keys_claimed.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="game_keys_claimed").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("game_keys_claimed").set(1)

        try:
            q_user_game_keys_claimed = self.db.get_user_game_keys_redeemed_count() or []
            for row in q_user_game_keys_claimed:
                user = {"user_id": row["_id"]['user_id'], "username": row["_id"]['user_id']}
                if row["user"] is not None and len(row["user"]) > 0:
                    user = row["user"][0]

                user_labels = {
                    "guild_id": row['_id']['guild_id'],
                    "user_id": user['user_id'],
                    "username": user['username'],
                }
                self.sum_user_game_keys_claimed.labels(**user_labels).set(row['total'])
            self.errors.labels("user_game_keys_claimed").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("user_game_keys_claimed").set(1)

        try:
            q_user_game_keys_submitted = self.db.get_user_game_keys_submitted_count() or []
            for row in q_user_game_keys_submitted:
                user = {"user_id": row["_id"]['user_id'], "username": row["_id"]['user_id']}
                if row["user"] is not None and len(row["user"]) > 0:
                    user = row["user"][0]

                user_labels = {
                    "guild_id": row['_id']['guild_id'],
                    "user_id": user['user_id'],
                    "username": user['username'],
                }
                self.sum_user_game_keys_submitted.labels(**user_labels).set(row['total'])
            self.errors.labels("user_game_keys_submitted").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("user_game_keys_submitted").set(1)

        try:
            q_minecraft_whitelisted = self.db.get_minecraft_whitelisted_count() or []
            for row in q_minecraft_whitelisted:
                self.sum_minecraft_whitelist.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels("minecraft_whitelisted").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("minecraft_whitelisted").set(1)

        try:
            q_stream_team_requests = self.db.get_team_requests_count() or []
            for row in q_stream_team_requests:
                self.sum_stream_team_requests.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels("stream_team_requests").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("stream_team_requests").set(1)

        try:
            q_birthdays = self.db.get_birthdays_count() or []
            for row in q_birthdays:
                self.sum_birthdays.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels("birthdays").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("birthdays").set(1)

        try:
            q_first_messages_today = self.db.get_first_messages_today_count() or []
            for row in q_first_messages_today:
                self.sum_first_messages.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels("first_messages_today").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("first_messages_today").set(1)

        try:
            logs = self.db.get_logs() or []
            for gid in known_guilds:
                for level in LogLevel.names_to_list():
                    t_labels = {"guild_id": gid, "level": level}
                    self.sum_logs.labels(**t_labels).set(0)
            for row in logs:
                self.sum_logs.labels(guild_id=row['_id']['guild_id'], level=row['_id']['level']).set(row["total"])
            self.errors.labels("logs").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("logs").set(1)

        try:
            q_known_users = self.db.get_known_users() or []
            for row in q_known_users:
                self.known_users.labels(guild_id=row['_id']['guild_id'], type=row['_id']['type']).set(row['total'])
            self.errors.labels("known_users").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("known_users").set(1)

        try:
            # loop top messages and add to histogram
            q_top_messages = self.db.get_user_messages_tracked() or []
            for u in q_top_messages:
                user = {"user_id": u["_id"]['user_id'], "username": u["_id"]['user_id']}
                if u["user"] is not None and len(u["user"]) > 0:
                    user = u["user"][0]

                user_labels = {
                    "guild_id": u['_id']['guild_id'],
                    "user_id": user['user_id'],
                    "username": user['username'],
                }
                self.top_messages.labels(**user_labels).set(u["total"])
            self.errors.labels("top_messages").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("top_messages").set(1)

        try:
            q_top_gifters = self.db.get_top_taco_gifters() or []
            for u in q_top_gifters:
                user = {"user_id": u["_id"]['user_id'], "username": u["_id"]['user_id']}
                if u["user"] is not None and len(u["user"]) > 0:
                    user = u["user"][0]

                user_labels = {
                    "guild_id": u['_id']['guild_id'],
                    "user_id": u["_id"]['user_id'],
                    "username": user['username'],
                }
                self.top_gifters.labels(**user_labels).set(u["total"])
            self.errors.labels("top_gifters").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("top_gifters").set(1)

        try:
            q_top_reactors = self.db.get_top_taco_reactors() or []
            for u in q_top_reactors:
                user = {"user_id": u["_id"]['user_id'], "username": u["_id"]['user_id']}
                if u["user"] is not None and len(u["user"]) > 0:
                    user = u["user"][0]

                user_labels = {
                    "guild_id": u['_id']['guild_id'],
                    "user_id": user['user_id'],
                    "username": user['username'],
                }
                self.top_reactors.labels(**user_labels).set(u["total"])
            self.errors.labels("top_reactors").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("top_reactors").set(1)

        try:
            q_top_tacos = self.db.get_top_taco_receivers() or []
            for u in q_top_tacos:
                user = {"user_id": u["_id"]['user_id'], "username": u["_id"]['user_id']}
                if u["user"] is not None and len(u["user"]) > 0:
                    user = u["user"][0]

                user_labels = {
                    "guild_id": u['_id']['guild_id'],
                    "user_id": user['user_id'],
                    "username": user['username'],
                }
                self.top_tacos.labels(**user_labels).set(u["total"])
            self.errors.labels("top_tacos").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("top_tacos").set(1)

        try:
            q_top_live = self.db.get_live_activity() or []
            for u in q_top_live:
                user = {"user_id": u["_id"]['user_id'], "username": u["_id"]['user_id']}
                if u["user"] is not None and len(u["user"]) > 0:
                    user = u["user"][0]

                user_labels = {
                    "guild_id": u['_id']['guild_id'],
                    "user_id": user['user_id'],
                    "username": user['username'],
                    "platform": u["_id"]['platform'],
                }
                self.top_live_activity.labels(**user_labels).set(u["total"])
            self.errors.labels("top_live_activity").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("top_live").set(1)

        try:
            q_suggestions = self.db.get_suggestions() or []
            for gid in known_guilds:
                for state in ["ACTIVE", "APPROVED", "REJECTED", "IMPLEMENTED", "CONSIDERED", "DELETED", "CLOSED"]:
                    suggestion_labels = {"guild_id": gid, "status": state}
                    self.suggestions.labels(**suggestion_labels).set(0)
            for row in q_suggestions:
                suggestion_labels = {"guild_id": row['_id']['guild_id'], "status": row['_id']['state']}
                self.suggestions.labels(**suggestion_labels).set(row["total"])
            self.errors.labels("suggestions").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("suggestions").set(1)

        try:
            q_join_leave = self.db.get_user_join_leave() or []
            for gid in known_guilds:
                for state in ["JOIN", "LEAVE"]:
                    join_leave_labels = {"guild_id": gid, "action": state}
                    self.user_join_leave.labels(**join_leave_labels).set(0)

            for row in q_join_leave:
                join_leave_labels = {"guild_id": row['_id']['guild_id'], "action": row['_id']['action']}
                self.user_join_leave.labels(**join_leave_labels).set(row["total"])
            self.errors.labels("join_leave").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("join_leave").set(1)

        try:
            q_photo_post = self.db.get_photo_posts_count() or []
            for u in q_photo_post:
                user = {"user_id": u["_id"]['user_id'], "username": u["_id"]['user_id']}
                if u["user"] is not None and len(u["user"]) > 0:
                    user = u["user"][0]

                user_labels = {
                    "guild_id": u['_id']['guild_id'],
                    "user_id": user['user_id'],
                    "username": user['username'],
                    "channel": u["_id"]['channel'],
                }
                self.photo_posts.labels(**user_labels).set(u["total"])
            self.errors.labels("photo_posts").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("photo_posts").set(1)

        try:
            q_taco_logs = self.db.get_taco_logs_counts() or []
            for t in q_taco_logs:
                taco_labels = {"guild_id": t["_id"]['guild_id'], "type": t["_id"]['type'] or "UNKNOWN"}
                self.taco_logs.labels(**taco_labels).set(t["total"])
            self.errors.labels("taco_logs").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex))
            self.errors.labels("taco_logs").set(1)

        try:
            q_trivia = self.db.get_trivia_questions() or []
            for t in q_trivia:
                trivia_labels = {
                    "guild_id": t['_id']["guild_id"],
                    "category": t['_id']["category"],
                    "difficulty": t['_id']["difficulty"],
                    "starter_id": t['_id']["starter_id"],
                    "starter_name": t['starter'][0]["username"],
                }
                self.trivia_questions.labels(**trivia_labels).set(t["total"])
            self.errors.labels("trivia_questions").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("trivia_questions").set(1)

        try:
            q_invites = self.db.get_invites_by_user() or []
            for row in q_invites:
                user = {"user_id": row["_id"]['user_id'], "username": row["_id"]['user_id']}
                if row["user"] is not None and len(row["user"]) > 0:
                    user = row["user"][0]

                invite_labels = {
                    "guild_id": row['_id']["guild_id"],
                    "user_id": row['_id']["user_id"],
                    # "username": row['user'][0]["username"],
                    "username": user["username"],
                }
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    self.invites.labels(**invite_labels).set(total_count)
            self.errors.labels("invites").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("invites").set(1)

        try:
            q_system_actions = self.db.get_system_action_counts() or []
            for row in q_system_actions:
                action_labels = {"guild_id": row['_id']["guild_id"], "action": row['_id']["action"]}
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    self.system_actions.labels(**action_labels).set(row["total"])
            self.errors.labels("system_actions").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("system_actions").set(1)

        try:
            q_user_status = self.db.get_users_by_status() or []
            for gid in known_guilds:
                for status in ["UNKNOWN", "ONLINE", "OFFLINE", "IDLE", "DND"]:
                    status_labels = {"guild_id": gid, "status": status}
                    self.user_status.labels(**status_labels).set(0)
            for row in q_user_status:
                status_labels = {"guild_id": row['_id']["guild_id"], "status": row['_id']["status"]}
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    self.user_status.labels(**status_labels).set(row["total"])
            self.errors.labels("user_status").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("user_status").set(1)

        try:
            q_introductions = self.db.get_introductions() or []
            for gid in known_guilds:
                for approved in ["true", "false"]:
                    intro_labels = {"guild_id": gid, "approved": approved}
                    self.introductions.labels(**intro_labels).set(0)

            for row in q_introductions:
                intro_labels = {"guild_id": row['_id']["guild_id"], "approved": str(row['_id']["approved"]).lower()}
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    self.introductions.labels(**intro_labels).set(row["total"])
            self.errors.labels("introductions").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("introductions").set(1)

        try:
            q_twitch_stream_avatar_duel_winners = self.db.get_stream_avatar_duel_winners() or []
            # for gid in known_guilds:
            for row in q_twitch_stream_avatar_duel_winners:
                winner = {"user_id": row["_id"]['winner_user_id'], "username": row["_id"]['winner_user_id']}
                if row["winner"] is not None and len(row["winner"]) > 0:
                    winner = row["winner"][0]
                channel = {"channel": row["_id"]['channel'], "channel_user_id": row["_id"]['channel_user_id']}
                if row["channel"] is not None and len(row["channel"]) > 0:
                    channel = row["channel"][0]
                user_labels = {
                    "guild_id": row['_id']['guild_id'],
                    "user_id": winner['user_id'],
                    "username": winner['username'],
                    "channel": channel['username'],
                    "channel_user_id": channel['user_id'],
                }
                self.twitch_stream_avatar_duel_winners.labels(**user_labels).set(row["total"])
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("twitch_stream_avatar_duel_winners").set(1)

        try:
            q_free_game_keys = self.db.get_free_game_keys() or []
            for state in ["ACTIVE", "EXPIRED"]:
                state_label = {"state": state}
                self.free_game_keys.labels(**state_label).set(0)
            for row in q_free_game_keys:
                self.free_game_keys.labels(state=row["_id"]['state']).set(row["total"])
            self.errors.labels("free_game_keys").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("free_game_keys").set(1)

        try:
            q_permission_counts = self.db.get_permission_counts() or []
            for gid in known_guilds:
                # loop all where not TacoPermissions.UNKNOWN
                for p in TacoPermissions.all_permissions():
                    if p != TacoPermissions.UNKNOWN:
                        self.permission_count.labels(guild_id=gid, permission=p).set(0)
                for row in q_permission_counts:
                    if row["_id"]["guild_id"] == gid:
                        self.permission_count.labels(guild_id=gid, permission=row["_id"]["permission"]).set(row["total"])
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels("permission").set(1)
