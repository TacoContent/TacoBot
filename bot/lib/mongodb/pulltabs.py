import inspect
import os
import traceback
import typing

from bot.lib.enums.loglevel import LogLevel
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from bot.lib.mongodb.database import Database


class PullTabTicketsDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def save_ticket(self, payload: dict) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            # save ticket payload (guard belongs in update_ticket)

            code = payload.get("code", None)
            if not code:
                self.log(0, LogLevel.WARNING, f"{self._module}.{self._class}.{_method}", "No code found in payload")
                return
            code = str(code)
            user_id = str(payload.get("user_id", ""))
            guild_id = str(payload.get("guild_id", ""))

            self.connection.pulltab_tickets.update_one(  # type: ignore
                {"code": code, "user_id": user_id, "guild_id": guild_id}, {"$setOnInsert": payload}, upsert=True
            )
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return

    def update_ticket(self, guild_id: int, user_id: int, code: str, updates: dict) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            # guard: if updates is empty, don't call update_one
            if not updates:
                self.log(0, LogLevel.WARNING, f"{self._module}.{self._class}.{_method}", "No updates provided")
                return

            self.connection.pulltab_tickets.update_one(  # type: ignore
                {"code": code, "user_id": str(user_id), "guild_id": str(guild_id)}, {"$set": updates}
            )
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return

    def get_ticket(self, guild_id: int, user_id: int, code: str) -> typing.Optional[PullTabTicketEntry]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            code = str(code)

            result = self.connection.pulltab_tickets.find_one(  # type: ignore
                {"code": code, "user_id": str(user_id), "guild_id": str(guild_id)}
            )
            if result:
                # Use the model's `from_dict` helper to build a validated model
                # This ensures only supported fields are used and types are validated.
                return PullTabTicketEntry.from_dict(result)

            return None
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return None

    def is_ticket_redeemed(self, guild_id: int, user_id: int, code: str) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            code = str(code)
            # check if a ticket with the given code, user_id, and guild_id exists and has a non-null redeemed_at
            # if it is found, it means the ticket has been redeemed
            # if not found, it means the ticket has not been redeemed, but may or may not exist
            result = self.connection.pulltab_tickets.find_one(  # type: ignore
                {"code": code, "user_id": str(user_id), "guild_id": str(guild_id), "redeemed_at": {"$ne": None}}
            )
            return result is not None
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return False

    def metric_pulltab_tickets_counts(self) -> typing.Optional[typing.Iterator[dict[str, typing.Any]]]:
        # Defined Prometheus Metric
        # self.pulltabs_tickets = Gauge(
        #     namespace=self.namespace,
        #     name="pulltabs_tickets",
        #     documentation="The number of pulltabs tickets",
        #     labelnames=["guild_id", "user_id", "username", "state", "status"],
        # )

        # Sample Document
        # {
        #     _id: ObjectId('691b6c16a7e261b468dbed87'),
        #     code: 'eOOcQzLUvCGgD',
        #     guild_id: '942532970613473293',
        #     user_id: '262031734260891648',
        #     cost: 100,
        #     created_at: 1763404822,
        #     effective_multiplier: 4,
        #     purchase_multiplier: 10,
        #     reward: 40,
        #     ticket: [
        #         '🍇🍎🍊',
        #         '🍒🍎🍉',
        #         '🍒🍉🌮',
        #         '🍇🍇🍒',
        #         '🍒🍉🍇'
        #     ],
        #     winning_lines: [
        #         {
        #             '🌮': 40
        #         }
        #     ]
        # }

        # status: 'REDEEMED' | 'PENDING' - based on whether redeemed_at is set
        # state: 'WINNING' | 'LOSING' - based on whether reward > 0
        # username: user.username from the users collection
        # {
        #     "$lookup": {
        #         "from": "users",
        #         "let": {"user_id": "$_id.user_id", "guild_id": "$_id.guild_id"},
        #         "pipeline": [
        #             {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}}},
        #             {"$match": {"$expr": {"$eq": ["$guild_id", "$$guild_id"]}}},
        #         ],
        #         "as": "user",
        #     }
        # },
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "guild_id": "$guild_id",
                            "user_id": "$user_id",
                            "state": {"$cond": [{"$gt": ["$reward", 0]}, "WINNER", "LOSER"]},
                            "status": {"$cond": [{"$ifNull": ["$redeemed_at", False]}, "REDEEMED", "PENDING"]},
                        },
                        "total": {"$sum": 1},
                    }
                },
                {
                    "$lookup": {
                        "from": "users",
                        "let": {"user_id": "$_id.user_id", "guild_id": "$_id.guild_id"},
                        "pipeline": [
                            {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}}},
                            {"$match": {"$expr": {"$eq": ["$guild_id", "$$guild_id"]}}},
                        ],
                        "as": "user",
                    }
                },
            ]

            cursor = self.connection.pulltab_tickets.aggregate(pipeline)  # type: ignore
            for document in cursor:
                yield document
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return None

    def metric_pulltab_purchase_multiplier_by_user(self) -> typing.Optional[typing.Iterator[dict[str, typing.Any]]]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "guild_id": "$guild_id",
                            "user_id": "$user_id",
                            "purchase_multiplier": "$purchase_multiplier",
                        },
                        "total": {"$sum": 1},
                    }
                },
                {
                    "$lookup": {
                        "from": "users",
                        "let": {"user_id": "$_id.user_id", "guild_id": "$_id.guild_id"},
                        "pipeline": [
                            {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}}},
                            {"$match": {"$expr": {"$eq": ["$guild_id", "$$guild_id"]}}},
                        ],
                        "as": "user",
                    }
                },
            ]

            cursor = self.connection.pulltab_tickets.aggregate(pipeline)  # type: ignore
            for document in cursor:
                yield document
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return None

    def metric_pulltab_spendings_by_user_and_status(self) -> typing.Optional[typing.Iterator[dict[str, typing.Any]]]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            pipeline = [
                {"$group": {"_id": {"guild_id": "$guild_id", "user_id": "$user_id"}, "total": {"$sum": "$cost"}}},
                {
                    "$lookup": {
                        "from": "users",
                        "let": {"user_id": "$_id.user_id", "guild_id": "$_id.guild_id"},
                        "pipeline": [
                            {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}}},
                            {"$match": {"$expr": {"$eq": ["$guild_id", "$$guild_id"]}}},
                        ],
                        "as": "user",
                    }
                },
            ]

            cursor = self.connection.pulltab_tickets.aggregate(pipeline)  # type: ignore
            for document in cursor:
                yield document
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return None

    def metric_pulltab_winnings_by_user_and_status(self) -> typing.Optional[typing.Iterator[dict[str, typing.Any]]]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "guild_id": "$guild_id",
                            "user_id": "$user_id",
                            "status": {"$cond": [{"$ifNull": ["$redeemed_at", False]}, "REDEEMED", "PENDING"]},
                        },
                        "total": {"$sum": "$reward"},
                    }
                },
                {
                    "$lookup": {
                        "from": "users",
                        "let": {"user_id": "$_id.user_id", "guild_id": "$_id.guild_id"},
                        "pipeline": [
                            {"$match": {"$expr": {"$eq": ["$user_id", "$$user_id"]}}},
                            {"$match": {"$expr": {"$eq": ["$guild_id", "$$guild_id"]}}},
                        ],
                        "as": "user",
                    }
                },
            ]

            cursor = self.connection.pulltab_tickets.aggregate(pipeline)  # type: ignore
            for document in cursor:
                yield document
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return None

    def metric_pulltab_winning_lines(self) -> typing.Optional[typing.Iterator[dict[str, typing.Any]]]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            # winning_lines is stored as a list of objects like: [{"🌮": 10}, {"🍎🍎🍎": 500}]
            # We need to count unique occurrences of the winning line keys per ticket
            # and return a total count grouped by guild and winning line.
            pipeline = [
                # Only consider documents that contain winning_lines
                {"$match": {"winning_lines": {"$exists": True, "$ne": []}}},
                # unwind the array so each element can be processed
                {"$unwind": "$winning_lines"},
                # convert the single-key object into a {k: ..., v: ...} form
                {"$project": {"guild_id": 1, "code": 1, "winning_kv": {"$objectToArray": "$winning_lines"}}},
                # unwind the object to get the key/value pair
                {"$unwind": "$winning_kv"},
                # group by ticket code + guild + line to deduplicate multiple entries in the same ticket
                {"$group": {"_id": {"guild_id": "$guild_id", "code": "$code", "line": "$winning_kv.k"}}},
                # now group by guild and line and count distinct tickets
                {"$group": {"_id": {"guild_id": "$_id.guild_id", "line": "$_id.line"}, "total": {"$sum": 1}}},
            ]

            cursor = self.connection.pulltab_tickets.aggregate(pipeline)  # type: ignore
            for document in cursor:
                yield document
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return None

    def get_config(self, guild_id: int) -> typing.Optional[dict[str, typing.Any]]:
        _method = inspect.stack()[0][3]
        try:
            config = self.settings.get_settings(guildId=guild_id, name="pulltab")
            if config:
                return config
            return None
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return None
