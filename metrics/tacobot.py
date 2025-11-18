import inspect
import os
import socket
import time
import traceback
import typing

from bot.lib import logger
from bot.lib.enums.loglevel import LogLevel
from bot.lib.enums.permissions import TacoPermissions
from bot.lib.mongodb.metrics import MetricsDatabase
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase
from bot.lib.settings import Settings
from bot.lib.utils import dict_get
from prometheus_client import Gauge


class TacoBotMetrics:
    def __init__(
        self, config, metrics_db: MetricsDatabase, pulltab_db: PullTabTicketsDatabase, settings: Settings
    ) -> None:
        # get the class name
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]

        self.settings = settings

        log_level = LogLevel.DEBUG
        try:
            log_level = LogLevel[self.settings.log_level.upper()]
            self.log = logger.Log(minimumLogLevel=log_level)
        except Exception as e:
            self.log = logger.Log(minimumLogLevel=log_level)
            self.log.error(
                0, f"{self._module}.{self._class}.{_method}", f"Error setting log level: {e}", traceback.format_exc()
            )

        self.namespace = "tacobot"
        self.polling_interval_seconds = config.metrics["pollingInterval"]
        self.config = config

        # merge labels and config labels
        # labels = labels + [x['name'] for x in self.config.labels]
        self.db = metrics_db
        self.pulltab_db = pulltab_db

        self._initialize_gauges()

        self._fetch_build_info()

    def _initialize_gauges(self):
        """Initialize all Prometheus Gauges"""
        _method = inspect.stack()[1][3]
        try:

            labels = ["guild_id"]

            user_labels = ["guild_id", "user_id", "username"]
            photo_post_labels = ["guild_id", "user_id", "username", "channel"]
            live_labels = ["guild_id", "user_id", "username", "platform"]

            self.sum_tacos = Gauge(
                namespace=self.namespace,
                name="tacos",
                documentation="The number of tacos give to users",
                labelnames=labels,
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
                namespace=self.namespace,
                name="logs",
                documentation="The number of logs",
                labelnames=["guild_id", "level"],
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
                namespace=self.namespace,
                name="gifters",
                documentation="The number of top gifters",
                labelnames=user_labels,
            )

            self.top_reactors = Gauge(
                namespace=self.namespace,
                name="reactors",
                documentation="The number of top reactors",
                labelnames=user_labels,
            )

            self.top_tacos = Gauge(
                namespace=self.namespace,
                name="top_tacos",
                documentation="The number of top tacos",
                labelnames=user_labels,
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

            self.shift_codes_tracked = Gauge(
                namespace=self.namespace,
                name="shift_codes_tracked",
                documentation="The number of shift codes tracked",
                labelnames=["guild_id", "state"],
            )

            self.shift_codes_count = Gauge(
                namespace=self.namespace,
                name="shift_codes",
                documentation="The number of shift codes",
                labelnames=["state"],
            )

            self.pulltabs_tickets = Gauge(
                namespace=self.namespace,
                name="pulltabs_tickets",
                documentation="The number of pulltabs tickets",
                labelnames=["guild_id", "user_id", "username", "state", "status"],
            )

            self.pulltabs_winnings = Gauge(
                namespace=self.namespace,
                name="pulltabs_winnings",
                documentation="The amount of pulltabs winnings",
                labelnames=["guild_id", "user_id", "username", "status"],
            )

            self.pulltabs_spendings = Gauge(
                namespace=self.namespace,
                name="pulltabs_spendings",
                documentation="The amount of tacos spent on pulltabs by users",
                labelnames=["guild_id", "user_id", "username"],
            )

            self.pulltabs_purchase_multiplier = Gauge(
                namespace=self.namespace,
                name="pulltabs_purchase_multiplier",
                documentation="The purchase multiplier of pulltabs tickets",
                labelnames=["guild_id", "user_id", "username", "purchase_multiplier"],
            )

            self.pulltabs_winning_lines = Gauge(
                namespace=self.namespace,
                name="pulltabs_winning_lines",
                documentation="The number of pulltabs winning lines",
                labelnames=["guild_id", "line"],
            )

            self.pulltabs_config_purchase_cost = Gauge(
                namespace=self.namespace,
                name="pulltabs_config_purchase_cost",
                documentation="The cost of pulltabs tickets",
                labelnames=["guild_id"],
            )

            self.pulltabs_config_purchase_max = Gauge(
                namespace=self.namespace,
                name="pulltabs_config_purchase_max",
                documentation="The maximum purchase count for pulltabs tickets",
                labelnames=["guild_id"],
            )

            self.pulltabs_config_multiplier_max = Gauge(
                namespace=self.namespace,
                name="pulltabs_config_multiplier_max",
                documentation="The maximum purchase multiplier for pulltabs tickets",
                labelnames=["guild_id"],
            )

            self.pulltabs_config_multiplier_increase = Gauge(
                namespace=self.namespace,
                name="pulltabs_config_multiplier_increase",
                documentation="The multiplier increase for pulltabs tickets",
                labelnames=["guild_id"],
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

        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

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

            self._set_gauge_labels(self.healthy, {}, 1 if data == b"healthy" else 0)
            self._set_gauge_labels(self.errors, {"source": "healthy"}, 0)

        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.healthy, {}, 0)
            self._set_gauge_labels(self.errors, {"source": "healthy"}, 1)

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
        self.check_health()

        self.db.open()
        known_guilds = self._fetch_known_guilds()

        self._fetch_all_tacos()

        self._fetch_all_gift_tacos()

        self._fetch_reaction_tacos()

        self._fetch_live_now()

        self._fetch_twitch_channels()

        self._fetch_all_twitch_tacos()

        self._fetch_twitch_linked_accounts()

        self._fetch_tqotd_questions()

        self._fetch_tqotd_answers()

        self._fetch_invited_users()

        self._fetch_live_platform()

        self._fetch_wdyctw_questions()

        self._fetch_wdyctw_answers()

        self._fetch_tech_thurs_questions()

        self._fetch_tech_thurs_answers()

        self._fetch_mental_monday_questions()

        self._fetch_mental_monday_answers()

        self._fetch_taco_tuesday_questions()

        self._fetch_taco_tuesday_answers()

        self._fetch_game_keys_available()

        self._fetch_game_keys_claimed()

        self._fetch_user_game_keys_claimed()

        self._fetch_user_game_keys_submitted()

        self._fetch_minecraft_whitelisted()

        self._fetch_stream_team_requests()

        self._fetch_birthdays()

        self._fetch_first_messages()

        self._fetch_logs(known_guilds=known_guilds)

        self._fetch_known_users()

        self._fetch_top_messages()

        self._fetch_top_gifters()

        self._fetch_top_reactors()

        self._fetch_top_tacos()

        self._fetch_top_live()

        self._fetch_suggestions(known_guilds=known_guilds)

        self._fetch_user_join_leave(known_guilds=known_guilds)

        self._fetch_photo_posts()

        self._fetch_taco_log_counts()

        self._fetch_trivia_question_counts()

        self._fetch_invite_counts()

        self._fetch_system_action_counts()

        self._fetch_user_status(known_guilds=known_guilds)

        self._fetch_introductions(known_guilds=known_guilds)

        self._fetch_twitch_stream_avatar_duel_winners()

        self._fetch_free_game_keys()

        self._fetch_shift_codes()

        self._fetch_tracked_shift_codes(known_guilds=known_guilds)

        self._fetch_pulltab_tickets()

        self._fetch_pulltab_winnings()

        self._fetch_pulltab_spendings()

        self._fetch_pulltab_purchase_multiplier()

        self._fetch_pulltab_winning_lines()

        self._fetch_pulltab_config(known_guilds=known_guilds)

        self._fetch_permission_counts(known_guilds=known_guilds)

    def _fetch_pulltab_config(self, known_guilds: list[str]) -> None:
        _method = inspect.stack()[0][3]
        try:
            for guild_id in known_guilds:
                if not guild_id.isdigit():
                    continue
                config = self.pulltab_db.get_config(guild_id=int(guild_id))
                if config:
                    purchase_config = config.get("purchase", {})
                    purchase_max = purchase_config.get("max", 0)
                    purchase_cost = purchase_config.get("cost", 0)

                    multiplier_config = config.get("multiplier", {})
                    multiplier_max = multiplier_config.get("max", 0)
                    multiplier_increase = multiplier_config.get("base_increase", 0)

                    self._set_gauge_labels(self.pulltabs_config_purchase_cost, {"guild_id": guild_id}, purchase_cost)
                    self._set_gauge_labels(self.pulltabs_config_purchase_max, {"guild_id": guild_id}, purchase_max)
                    self._set_gauge_labels(self.pulltabs_config_multiplier_max, {"guild_id": guild_id}, multiplier_max)
                    self._set_gauge_labels(
                        self.pulltabs_config_multiplier_increase, {"guild_id": guild_id}, multiplier_increase
                    )

            self._set_gauge_labels(self.errors, {"source": "pulltabs_config_purchase_cost"}, 0)
            self._set_gauge_labels(self.errors, {"source": "pulltabs_config_purchase_max"}, 0)
            self._set_gauge_labels(self.errors, {"source": "pulltabs_config_multiplier_max"}, 0)
            self._set_gauge_labels(self.errors, {"source": "pulltabs_config_multiplier_increase"}, 0)

        except Exception as ex:
            _method = inspect.stack()[0][3]
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "pulltabs_config_purchase_cost"}, 1)
            self._set_gauge_labels(self.errors, {"source": "pulltabs_config_purchase_max"}, 1)
            self._set_gauge_labels(self.errors, {"source": "pulltabs_config_multiplier_max"}, 1)
            self._set_gauge_labels(self.errors, {"source": "pulltabs_config_multiplier_increase"}, 1)

    def _fetch_pulltab_tickets(self) -> None:
        """Fetch pulltab tickets helper method."""
        _method = inspect.stack()[0][3]
        try:
            self.pulltabs_tickets.clear()

            q_pulltab_tickets = self.pulltab_db.metric_pulltab_tickets_counts() or []
            for row in q_pulltab_tickets:
                user = {"user_id": row["_id"]['user_id'], "username": row["_id"]['user_id']}
                if "user" in row and len(row["user"]) > 0:
                    user = row["user"][0]
                self._set_gauge_labels(
                    self.pulltabs_tickets,
                    {
                        "guild_id": row['_id']['guild_id'],
                        "user_id": user['user_id'],
                        "username": user['username'],
                        "state": row['_id']['state'],
                        "status": row['_id']['status'],
                    },
                    row['total'],
                )
            self._set_gauge_labels(self.errors, {"source": "pulltab_tickets"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "pulltab_tickets"}, 1)

    def _fetch_pulltab_purchase_multiplier(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            self.pulltabs_purchase_multiplier.clear()
            q_pulltab_multipliers = self.pulltab_db.metric_pulltab_purchase_multiplier_by_user() or []
            for row in q_pulltab_multipliers:
                # Row contains _id: {guild_id, user_id, purchase_multiplier}, total
                # For username we store internal user hash; set to user_id for now
                user = {"user_id": row["_id"]["user_id"], "username": row["_id"]["user_id"]}
                if "user" in row and len(row["user"]) > 0:
                    user = row["user"][0]
                user_labels = {
                    "guild_id": row["_id"]["guild_id"],
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "purchase_multiplier": str(row["_id"]["purchase_multiplier"]),
                }
                self._set_gauge_labels(self.pulltabs_purchase_multiplier, user_labels, row["total"])
            self._set_gauge_labels(self.errors, {"source": "pulltab_purchase_multiplier"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "pulltab_purchase_multiplier"}, 1)

    def _fetch_pulltab_spendings(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            q_pulltab_spendings = self.pulltab_db.metric_pulltab_spendings_by_user_and_status() or []
            for row in q_pulltab_spendings:
                # Row contains _id: {guild_id, user_id}, total
                # For username we store internal user hash; set to user_id for now
                user = {"user_id": row["_id"]["user_id"], "username": row["_id"]["user_id"]}
                if "user" in row and len(row["user"]) > 0:
                    user = row["user"][0]
                user_labels = {
                    "guild_id": row["_id"]["guild_id"],
                    "user_id": user["user_id"],
                    "username": user["username"],
                }
                self._set_gauge_labels(self.pulltabs_spendings, user_labels, row["total"])
            self._set_gauge_labels(self.errors, {"source": "pulltab_spendings"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "pulltab_spendings"}, 1)

    def _fetch_pulltab_winnings(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            q_pulltab_winnings = self.pulltab_db.metric_pulltab_winnings_by_user_and_status() or []
            for row in q_pulltab_winnings:
                # Row contains _id: {guild_id, user_id}, total
                # For username we store internal user hash; set to user_id for now
                user = {"user_id": row["_id"]["user_id"], "username": row["_id"]["user_id"]}
                if "user" in row and len(row["user"]) > 0:
                    user = row["user"][0]
                user_labels = {
                    "guild_id": row["_id"]["guild_id"],
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "status": "total",
                }
                self._set_gauge_labels(self.pulltabs_winnings, user_labels, row["total"])
            self._set_gauge_labels(self.errors, {"source": "pulltab_winnings"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "pulltab_winnings"}, 1)

    def _fetch_pulltab_winning_lines(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            q_pulltab_lines = self.pulltab_db.metric_pulltab_winning_lines() or []
            for row in q_pulltab_lines:
                labels = {"guild_id": row["_id"]["guild_id"], "line": row["_id"]["line"]}
                self._set_gauge_labels(self.pulltabs_winning_lines, labels, row["total"])
            self._set_gauge_labels(self.errors, {"source": "pulltab_winning_lines"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "pulltab_winning_lines"}, 1)

    def _fetch_live_now(self) -> None:
        """Fetch live now helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_live_now = self.db.get_live_now_count() or []
            for row in q_live_now:
                self._set_gauge_labels(self.sum_live_now, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "live_now"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "live_now"}, 1)

    def _fetch_twitch_channels(self) -> None:
        """Fetch twitch channels helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_twitch_channels = self.db.get_twitch_channel_bot_count() or []
            for row in q_twitch_channels:
                self._set_gauge_labels(self.sum_twitch_channels, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "twitch_channels"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "twitch_channels"}, 1)

    def _fetch_all_twitch_tacos(self) -> None:
        """Fetch all twitch tacos helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_all_twitch_tacos = self.db.get_sum_all_twitch_tacos() or []
            for row in q_all_twitch_tacos:
                # self.sum_twitch_tacos.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_twitch_tacos, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "twitch_tacos"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "twitch_tacos"}, 1)

    def _fetch_twitch_linked_accounts(self) -> None:
        """Fetch twitch linked accounts helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_twitch_linked_accounts = self.db.get_twitch_linked_accounts_count() or []
            for row in q_twitch_linked_accounts:
                self.sum_twitch_linked_accounts.set(row['total'])
            self._set_gauge_labels(self.errors, {"source": "twitch_linked_accounts"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "twitch_linked_accounts"}, 1)

    def _fetch_tqotd_questions(self) -> None:
        """Fetch TQOTD questions helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_tqotd_questions = self.db.get_tqotd_questions_count() or []
            for row in q_tqotd_questions:
                self._set_gauge_labels(self.sum_tqotd_questions, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "tqotd_questions"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "tqotd_questions"}, 1)

    def _fetch_tqotd_answers(self) -> None:
        """Fetch TQOTD answers helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_tqotd_answers = self.db.get_tqotd_answers_count() or []
            for row in q_tqotd_answers:
                self._set_gauge_labels(self.sum_tqotd_answers, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "tqotd_answers"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "tqotd_answers"}, 1)

    def _fetch_invited_users(self) -> None:
        """Fetch invited users helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_invited_users = self.db.get_invited_users_count() or []
            for row in q_invited_users:
                self._set_gauge_labels(self.sum_invited_users, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "invited_users"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "invited_users"}, 1)

    def _fetch_live_platform(self) -> None:
        """Fetch live platform helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_live_platform = self.db.get_sum_live_by_platform() or []
            for row in q_live_platform:
                self._set_gauge_labels(
                    self.sum_live_platform,
                    {"guild_id": row['_id']['guild_id'], "platform": row['_id']['platform']},
                    row['total'],
                )
            self._set_gauge_labels(self.errors, {"source": "live_platform"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "live_platform"}, 1)

    def _fetch_wdyctw_questions(self) -> None:
        """Fetch wdyctw questions helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_wdyctw = self.db.get_wdyctw_questions_count() or []
            for row in q_wdyctw:
                self._set_gauge_labels(self.sum_wdyctw, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "wdyctw"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "wdyctw"}, 1)

    def _fetch_wdyctw_answers(self) -> None:
        """Fetch wdyctw answers helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_wdyctw_answers = self.db.get_wdyctw_answers_count() or []
            for row in q_wdyctw_answers:
                self._set_gauge_labels(self.sum_wdyctw_answers, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "wdyctw_answers"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "wdyctw_answers"}, 1)

    def _fetch_tech_thurs_questions(self) -> None:
        """Fetch tech thurs questions helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_techthurs = self.db.get_techthurs_questions_count() or []
            for row in q_techthurs:
                self._set_gauge_labels(self.sum_techthurs, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "techthurs"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "techthurs"}, 1)

    def _fetch_tech_thurs_answers(self) -> None:
        """Fetch tech thurs answers helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_techthurs_answers = self.db.get_techthurs_answers_count() or []
            for row in q_techthurs_answers:
                self._set_gauge_labels(self.sum_techthurs_answers, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "techthurs_answers"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "techthurs_answers"}, 1)

    def _fetch_mental_monday_questions(self) -> None:
        """Fetch mental monday questions helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_mentalmondays = self.db.get_mentalmondays_questions_count() or []
            for row in q_mentalmondays:
                # self.sum_mentalmondays.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_mentalmondays, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "mentalmondays"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "mentalmondays"}, 1)

    def _fetch_mental_monday_answers(self) -> None:
        """Fetch mental monday answers helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_mentalmondays_answers = self.db.get_mentalmondays_answers_count() or []
            for row in q_mentalmondays_answers:
                # self.sum_mentalmondays_answers.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_mentalmondays_answers, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "mentalmondays_answers"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "mentalmondays_answers"}, 1)

    def _fetch_taco_tuesday_questions(self) -> None:
        """Fetch taco tuesday questions helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_tacotuesday = self.db.get_tacotuesday_questions_count() or []
            for row in q_tacotuesday:
                # self.sum_tacotuesday.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_tacotuesday, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "tacotuesday"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "tacotuesday"}, 1)

    def _fetch_taco_tuesday_answers(self) -> None:
        """Fetch taco tuesday answers helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_tacotuesday_answers = self.db.get_tacotuesday_answers_count() or []
            for row in q_tacotuesday_answers:
                # self.sum_tacotuesday_answers.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_tacotuesday_answers, {"guild_id": row['_id']}, row['total'])
            # self.errors.labels(source="tacotuesday_answers").set(0)
            self._set_gauge_labels(self.errors, {"source": "tacotuesday_answers"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels(source="tacotuesday_answers").set(1)
            self._set_gauge_labels(self.errors, {"source": "tacotuesday_answers"}, 1)

    def _fetch_game_keys_available(self) -> None:
        """Fetch game keys available helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_game_keys_available = self.db.get_game_keys_available_count() or []
            for row in q_game_keys_available:
                # self.sum_game_keys_available.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_game_keys_available, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "game_keys_available"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels(source="game_keys_available").set(1)
            self._set_gauge_labels(self.errors, {"source": "game_keys_available"}, 1)

    def _fetch_game_keys_claimed(self) -> None:
        """Fetch game keys claimed helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_game_keys_claimed = self.db.get_game_keys_redeemed_count() or []
            for row in q_game_keys_claimed:
                # self.sum_game_keys_claimed.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_game_keys_claimed, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "game_keys_claimed"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "game_keys_claimed"}, 1)

    def _fetch_user_game_keys_claimed(self) -> None:
        """Fetch user game keys claimed helper method."""
        _method = inspect.stack()[0][3]
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
                # self.sum_user_game_keys_claimed.labels(**user_labels).set(row['total'])
                self._set_gauge_labels(self.sum_user_game_keys_claimed, user_labels, row['total'])
            self._set_gauge_labels(self.errors, {"source": "user_game_keys_claimed"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "user_game_keys_claimed"}, 1)

    def _fetch_user_game_keys_submitted(self) -> None:
        """Fetch user game keys submitted helper method."""
        _method = inspect.stack()[0][3]
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
                # self.sum_user_game_keys_submitted.labels(**user_labels).set(row['total'])
                self._set_gauge_labels(self.sum_user_game_keys_submitted, user_labels, row['total'])
            # self.errors.labels("user_game_keys_submitted").set(0)
            self._set_gauge_labels(self.errors, {"source": "user_game_keys_submitted"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "user_game_keys_submitted"}, 1)

    def _fetch_minecraft_whitelisted(self) -> None:
        """Fetch minecraft whitelisted helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_minecraft_whitelisted = self.db.get_minecraft_whitelisted_count() or []
            for row in q_minecraft_whitelisted:
                # self.sum_minecraft_whitelist.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_minecraft_whitelist, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "minecraft_whitelisted"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("minecraft_whitelisted").set(1)
            self._set_gauge_labels(self.errors, {"source": "minecraft_whitelisted"}, 1)

    def _fetch_stream_team_requests(self) -> None:
        """Fetch stream team requests helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_stream_team_requests = self.db.get_team_requests_count() or []
            for row in q_stream_team_requests:
                # self.sum_stream_team_requests.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_stream_team_requests, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "stream_team_requests"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "stream_team_requests"}, 1)

    def _fetch_birthdays(self) -> None:
        """Fetch birthdays helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_birthdays = self.db.get_birthdays_count() or []
            for row in q_birthdays:
                # self.sum_birthdays.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_birthdays, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "birthdays"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "birthdays"}, 1)

    def _fetch_first_messages(self) -> None:
        """Fetch first messages helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_first_messages_today = self.db.get_first_messages_today_count() or []
            for row in q_first_messages_today:
                # self.sum_first_messages.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_first_messages, {"guild_id": row['_id']}, row['total'])
            # self.errors.labels("first_messages_today").set(0)
            self._set_gauge_labels(self.errors, {"source": "first_messages_today"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "first_messages_today"}, 1)

    def _fetch_logs(self, known_guilds: typing.List[str]) -> None:
        """Fetch logs helper method."""
        _method = inspect.stack()[0][3]
        try:
            logs = self.db.get_logs() or []
            for gid in known_guilds:
                for level in LogLevel.names_to_list():
                    t_labels = {"guild_id": gid, "level": level}
                    # self.sum_logs.labels(**t_labels).set(0)
                    self._set_gauge_labels(self.sum_logs, t_labels, 0)
            for row in logs:
                # self.sum_logs.labels(guild_id=row['_id']['guild_id'], level=row['_id']['level']).set(row["total"])
                self._set_gauge_labels(
                    self.sum_logs, {"guild_id": row['_id']['guild_id'], "level": row['_id']['level']}, row["total"]
                )
            # self.errors.labels("logs").set(0)
            self._set_gauge_labels(self.errors, {"source": "logs"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("logs").set(1)
            self._set_gauge_labels(self.errors, {"source": "logs"}, 1)

    def _fetch_known_users(self) -> None:
        """Fetch known users helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_known_users = self.db.get_known_users() or []
            for row in q_known_users:
                # self.known_users.labels(guild_id=row['_id']['guild_id'], type=row['_id']['type']).set(row['total'])
                self._set_gauge_labels(
                    self.known_users, {"guild_id": row['_id']['guild_id'], "type": row['_id']['type']}, row['total']
                )
            self._set_gauge_labels(self.errors, {"source": "known_users"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "known_users"}, 1)

    def _fetch_top_messages(self) -> None:
        """Fetch top messages helper method."""
        _method = inspect.stack()[0][3]
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
                # self.top_messages.labels(**user_labels).set(u["total"])
                self._set_gauge_labels(self.top_messages, user_labels, u["total"])
            self._set_gauge_labels(self.errors, {"source": "top_messages"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "top_messages"}, 1)

    def _fetch_top_gifters(self) -> None:
        """Fetch top gifters helper method."""
        _method = inspect.stack()[0][3]
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
                # self.top_gifters.labels(**user_labels).set(u["total"])
                self._set_gauge_labels(self.top_gifters, user_labels, u["total"])
            self._set_gauge_labels(self.errors, {"source": "top_gifters"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "top_gifters"}, 1)

    def _fetch_top_reactors(self) -> None:
        """Fetch top reactors helper method."""
        _method = inspect.stack()[0][3]
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
                # self.top_reactors.labels(**user_labels).set(u["total"])
                self._set_gauge_labels(self.top_reactors, user_labels, u["total"])
            self._set_gauge_labels(self.errors, {"source": "top_reactors"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "top_reactors"}, 1)

    def _fetch_top_tacos(self) -> None:
        """Fetch top tacos helper method."""
        _method = inspect.stack()[0][3]
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
                # self.top_tacos.labels(**user_labels).set(u["total"])
                self._set_gauge_labels(self.top_tacos, user_labels, u["total"])
            self._set_gauge_labels(self.errors, {"source": "top_tacos"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "top_tacos"}, 1)

    def _fetch_top_live(self) -> None:
        """Fetch top live activity helper method."""
        _method = inspect.stack()[0][3]
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
                # self.top_live_activity.labels(**user_labels).set(u["total"])
                self._set_gauge_labels(self.top_live_activity, user_labels, u["total"])
            self._set_gauge_labels(self.errors, {"source": "top_live_activity"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "top_live"}, 1)

    def _fetch_suggestions(self, known_guilds: typing.List[str]) -> None:
        """Fetch suggestions helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_suggestions = self.db.get_suggestions() or []
            for gid in known_guilds:
                for state in ["ACTIVE", "APPROVED", "REJECTED", "IMPLEMENTED", "CONSIDERED", "DELETED", "CLOSED"]:
                    suggestion_labels = {"guild_id": gid, "status": state}
                    # self.suggestions.labels(**suggestion_labels).set(0)
                    self._set_gauge_labels(self.suggestions, suggestion_labels, 0)
            for row in q_suggestions:
                suggestion_labels = {"guild_id": row['_id']['guild_id'], "status": row['_id']['state']}
                # self.suggestions.labels(**suggestion_labels).set(row["total"])
                self._set_gauge_labels(self.suggestions, suggestion_labels, row["total"])
            # self.errors.labels("suggestions").set(0)
            self._set_gauge_labels(self.errors, {"source": "suggestions"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "suggestions"}, 1)

    def _fetch_user_join_leave(self, known_guilds: typing.List[str]) -> None:
        """Fetch user join/leave helper method."""
        _method = inspect.stack()[0][3]
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

    def _fetch_photo_posts(self) -> None:
        """Fetch photo posts helper method."""
        _method = inspect.stack()[0][3]
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
                # self.photo_posts.labels(**user_labels).set(u["total"])
                self._set_gauge_labels(self.photo_posts, user_labels, u["total"])
            # self.errors.labels("photo_posts").set(0)
            self._set_gauge_labels(self.errors, {"source": "photo_posts"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "photo_posts"}, 1)

    def _fetch_reaction_tacos(self) -> None:
        """Fetch reaction tacos helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_all_reaction_tacos = self.db.get_sum_all_taco_reactions() or []
            for row in q_all_reaction_tacos:
                # self.sum_taco_reactions.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_taco_reactions, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "reaction_tacos"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "reaction_tacos"}, 1)

    def _fetch_all_gift_tacos(self) -> None:
        """Fetch all gift tacos helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_all_gift_tacos = self.db.get_sum_all_gift_tacos() or []
            for row in q_all_gift_tacos:
                # self.sum_taco_gifts.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_taco_gifts, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "gift_tacos"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "gift_tacos"}, 1)

    def _fetch_all_tacos(self) -> None:
        """Fetch all tacos helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_all_tacos = self.db.get_sum_all_tacos() or []
            for row in q_all_tacos:
                # self.sum_tacos.labels(guild_id=row['_id']).set(row['total'])
                self._set_gauge_labels(self.sum_tacos, {"guild_id": row['_id']}, row['total'])
            self._set_gauge_labels(self.errors, {"source": "tacos"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "tacos"}, 1)

    def _fetch_build_info(self) -> None:
        """Fetch build info helper method."""
        _method = inspect.stack()[0][3]
        try:
            ver = dict_get(os.environ, "APP_VERSION", "1.0.0-snapshot")
            ref = dict_get(os.environ, "APP_BUILD_REF", "unknown")
            build_date = dict_get(os.environ, "APP_BUILD_DATE", "unknown")
            sha = dict_get(os.environ, "APP_BUILD_SHA", "unknown")
            # self.build_info.labels(version=ver, ref=ref, build_date=build_date, sha=sha).set(1)
            self._set_gauge_labels(
                self.build_info, {"version": ver, "ref": ref, "build_date": build_date, "sha": sha}, 1
            )
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Metrics initialized")

            self._set_gauge_labels(self.errors, {"source": "build_info"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "build_info"}, 1)

    def _fetch_taco_log_counts(self) -> None:
        """Fetch taco log counts helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_taco_logs = self.db.get_taco_logs_counts() or []
            for t in q_taco_logs:
                taco_labels = {"guild_id": t["_id"]['guild_id'], "type": t["_id"]['type'] or "UNKNOWN"}
                # self.taco_logs.labels(**taco_labels).set(t["total"])
                self._set_gauge_labels(self.taco_logs, taco_labels, t["total"])
            # self.errors.labels("taco_logs").set(0)
            self._set_gauge_labels(self.errors, {"source": "taco_logs"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("taco_logs").set(1)
            self._set_gauge_labels(self.errors, {"source": "taco_logs"}, 1)

    def _fetch_trivia_question_counts(self) -> None:
        """Fetch trivia counts helper method."""
        _method = inspect.stack()[0][3]
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
                # self.trivia_questions.labels(**trivia_labels).set(t["total"])
                self._set_gauge_labels(self.trivia_questions, trivia_labels, t["total"])
            # self.errors.labels("trivia_questions").set(0)
            self._set_gauge_labels(self.errors, {"source": "trivia_questions"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "trivia_questions"}, 1)

    def _fetch_invite_counts(self) -> None:
        """Fetch invite counts helper method."""
        _method = inspect.stack()[0][3]
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
                    # self.invites.labels(**invite_labels).set(total_count)
                    self._set_gauge_labels(self.invites, invite_labels, total_count)
            # self.errors.labels("invites").set(0)
            self._set_gauge_labels(self.errors, {"source": "invites"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("invites").set(1)
            self._set_gauge_labels(self.errors, {"source": "invites"}, 1)

    def _fetch_system_action_counts(self) -> None:
        """Fetch system action counts helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_system_actions = self.db.get_system_action_counts() or []
            for row in q_system_actions:
                action_labels = {"guild_id": row['_id']["guild_id"], "action": row['_id']["action"]}
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    # self.system_actions.labels(**action_labels).set(row["total"])
                    self._set_gauge_labels(self.system_actions, action_labels, row["total"])
            # self.errors.labels("system_actions").set(0)
            self._set_gauge_labels(self.errors, {"source": "system_actions"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "system_actions"}, 1)

    def _fetch_user_status(self, known_guilds: typing.List[str]) -> None:
        """Fetch user status helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_user_status = self.db.get_users_by_status() or []
            for gid in known_guilds:
                for status in ["UNKNOWN", "ONLINE", "OFFLINE", "IDLE", "DND"]:
                    status_labels = {"guild_id": gid, "status": status}
                    # self.user_status.labels(**status_labels).set(0)
                    self._set_gauge_labels(self.user_status, status_labels, 0)
            for row in q_user_status:
                status_labels = {"guild_id": row['_id']["guild_id"], "status": row['_id']["status"]}
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    # self.user_status.labels(**status_labels).set(row["total"])
                    self._set_gauge_labels(self.user_status, status_labels, row["total"])
            # self.errors.labels("user_status").set(0)
            self._set_gauge_labels(self.errors, {"source": "user_status"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("user_status").set(1)
            self._set_gauge_labels(self.errors, {"source": "user_status"}, 1)

    def _fetch_introductions(self, known_guilds: typing.List[str]) -> None:
        """Fetch introductions helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_introductions = self.db.get_introductions() or []
            for gid in known_guilds:
                for approved in ["true", "false"]:
                    intro_labels = {"guild_id": gid, "approved": approved}
                    # self.introductions.labels(**intro_labels).set(0)
                    self._set_gauge_labels(self.introductions, intro_labels, 0)

            for row in q_introductions:
                intro_labels = {"guild_id": row['_id']["guild_id"], "approved": str(row['_id']["approved"]).lower()}
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    # self.introductions.labels(**intro_labels).set(row["total"])
                    self._set_gauge_labels(self.introductions, intro_labels, row["total"])
            # self.errors.labels("introductions").set(0)
            self._set_gauge_labels(self.errors, {"source": "introductions"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("introductions").set(1)
            self._set_gauge_labels(self.errors, {"source": "introductions"}, 1)

    def _fetch_twitch_stream_avatar_duel_winners(self) -> None:
        """Fetch Twitch stream avatar duel winners helper method."""
        _method = inspect.stack()[0][3]
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
                # self.twitch_stream_avatar_duel_winners.labels(**user_labels).set(row["total"])
                self._set_gauge_labels(self.twitch_stream_avatar_duel_winners, user_labels, row["total"])
            self._set_gauge_labels(self.errors, {"source": "twitch_stream_avatar_duel_winners"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("twitch_stream_avatar_duel_winners").set(1)
            self._set_gauge_labels(self.errors, {"source": "twitch_stream_avatar_duel_winners"}, 1)

    def _fetch_free_game_keys(self) -> None:
        """Fetch free game keys helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_free_game_keys = self.db.get_free_game_keys() or []
            for state in ["ACTIVE", "EXPIRED"]:
                state_label = {"state": state}
                # self.free_game_keys.labels(**state_label).set(0)
                self._set_gauge_labels(self.free_game_keys, state_label, 0)

            for row in q_free_game_keys:
                state_label = {"state": row["_id"]['state']}
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    # self.free_game_keys.labels(state=row["_id"]['state']).set(row["total"])
                    self._set_gauge_labels(self.free_game_keys, state_label, row["total"])
            # self.errors.labels("free_game_keys").set(0)
            self._set_gauge_labels(self.errors, {"source": "free_game_keys"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("free_game_keys").set(1)
            self._set_gauge_labels(self.errors, {"source": "free_game_keys"}, 1)

    def _fetch_shift_codes(self) -> None:
        """Fetch shift codes helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_shift_codes = self.db.get_shift_code_counts() or []
            for state in ["ACTIVE", "EXPIRED"]:
                shift_code_labels = {"state": state}
                # self.shift_codes_count.labels(**shift_code_labels).set(0)
                self._set_gauge_labels(self.shift_codes_count, shift_code_labels, 0)

            for row in q_shift_codes:
                shift_code_labels = {"state": row['_id']["state"]}
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    self._set_gauge_labels(self.shift_codes_count, shift_code_labels, row["total"])
                    # self.shift_codes_count.labels(**shift_code_labels).set(row["total"])
            # self.errors.labels("shift_codes").set(0)
            self._set_gauge_labels(self.errors, {"source": "shift_codes"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("shift_codes").set(1)
            self._set_gauge_labels(self.errors, {"source": "shift_codes"}, 1)

    def _fetch_tracked_shift_codes(self, known_guilds: typing.List[str]) -> None:
        """Fetch tracked shift codes helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_tracked_shift_codes = self.db.get_tracked_shift_codes_counts() or []
            for gid in known_guilds:
                for state in ["ACTIVE", "EXPIRED"]:
                    shift_code_labels = {"guild_id": gid, "state": state}
                    # self.shift_codes_tracked.labels(**shift_code_labels).set(0)
                    self._set_gauge_labels(self.shift_codes_tracked, shift_code_labels, 0)

            for row in q_tracked_shift_codes:
                shift_code_labels = {"guild_id": row['_id']["guild_id"], "state": row['_id']["state"]}
                total_count = row["total"]
                if total_count is not None and total_count > 0:
                    # self.shift_codes_tracked.labels(**shift_code_labels).set(row["total"])
                    self._set_gauge_labels(self.shift_codes_tracked, shift_code_labels, row["total"])
            # self.errors.labels("tracked_shift_codes").set(0)
            self._set_gauge_labels(self.errors, {"source": "tracked_shift_codes"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # self.errors.labels("tracked_shift_codes").set(1)
            self._set_gauge_labels(self.errors, {"source": "tracked_shift_codes"}, 1)

    def _fetch_permission_counts(self, known_guilds: typing.List[str]) -> None:
        """Fetch permission counts helper method."""
        _method = inspect.stack()[0][3]
        try:
            q_permission_counts = self.db.get_permission_counts() or []
            for gid in known_guilds:
                # loop all where not TacoPermissions.UNKNOWN
                for p in TacoPermissions.all_permissions():
                    if p != TacoPermissions.UNKNOWN:
                        self._set_gauge_labels(
                            self.permission_count, {"guild_id": gid, "permission": p.name.lower()}, 0
                        )
                        # self.permission_count.labels(guild_id=gid, permission=p).set(0)
            for row in q_permission_counts:
                self._set_gauge_labels(
                    self.permission_count,
                    {"guild_id": row['_id']["guild_id"], "permission": row['_id']["permission"]},
                    row["total"],
                )
                # self.permission_count.labels(
                #     guild_id=row['_id']["guild_id"],
                #     permission=row['_id']["permission"],
                # ).set(row["total"])

            self._set_gauge_labels(self.errors, {"source": "permission"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "permission"}, 1)
            # self.errors.labels(source="permission").set(1)

    def _set_gauge_labels(self, gauge: Gauge, labels: typing.Dict[str, str], value: float) -> None:
        """Set gauge labels helper method."""
        _method = inspect.stack()[0][3]
        try:
            if labels is not None and len(labels) > 0:
                gauge.labels(**labels).set(value)
            else:
                gauge.set(value)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

    def _fetch_known_guilds(self) -> typing.List[str]:
        """Fetch known guilds helper method."""
        _method = inspect.stack()[0][3]
        known_guilds: typing.List[str] = []
        try:
            q_guilds = self.db.get_guilds() or []
            for row in q_guilds:
                known_guilds.append(row['guild_id'])
                self._set_gauge_labels(self.guilds, {"guild_id": row['guild_id'], "name": row['name']}, 1)
            self._set_gauge_labels(self.errors, {"source": "guilds"}, 0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self._set_gauge_labels(self.errors, {"source": "guilds"}, 1)
        return known_guilds
