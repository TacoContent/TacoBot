from pymongo import MongoClient
from bson.objectid import ObjectId
import traceback
import json
import typing
import datetime
import pytz
import os
import uuid
from . import loglevel
from . import utils

# from .mongodb import migration


class MongoDatabase:
    def __init__(self):
        self.client = None
        self.connection = None
        pass

    def open(self):
        if "MONGODB_URL" not in os.environ or os.environ["MONGODB_URL"] == "":
            raise ValueError("MONGODB_URL is not set")
        self.client = MongoClient(os.environ["MONGODB_URL"])
        self.connection = self.client["tacobot"]

    def close(self):
        try:
            if self.client:
                self.client.close()
                self.client = None
                self.connection = None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def insert_log(
        self,
        guildId: int,
        level: loglevel.LogLevel,
        method: str,
        message: str,
        stack: typing.Optional[str] = None,
    ) -> None:
        try:
            if self.connection is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "timestamp": utils.get_timestamp(),
                "level": level.name,
                "method": method,
                "message": message,
                "stack_trace": stack if stack else "",
            }
            self.connection.logs.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_sum_all_tacos(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.tacos.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": "$count"}}}]
            )

        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_sum_all_gift_tacos(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.taco_gifts.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": "$count"}}}]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_sum_all_taco_reactions(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.tacos_reactions.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": 1}}}]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_sum_all_twitch_tacos(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.twitch_tacos_gifts.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": "$count"}}}]
            )

        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_live_now_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.live_tracked.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": 1}}}]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_twitch_channel_bot_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.twitch_channels.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": 1}}}]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_twitch_linked_accounts_count(self):
        try:
            if self.connection is None:
                self.open()
            # count all documents in twitch_users collection
            return self.connection.twitch_users.aggregate(
                [{"$group": {"_id": 1, "total": {"$sum": 1}}}]
            )

        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_tqotd_questions_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.tqotd.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": 1}}}]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_tqotd_answers_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.tqotd.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {"$sum": {"$size": "$answered"}},
                        }
                    }
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_invited_users_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.invite_codes.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {
                                "$sum": {
                                    "$size": {"$ifNull": ["$invites", []]},
                                },
                            },
                        },
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_sum_live_by_platform(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.live_activity.aggregate(
                [
                    {"$match": {"status": {"$eq": "ONLINE"}}},
                    {
                        "$group": {
                            "_id": {"platform": "$platform", "guild_id": "$guild_id"},
                            "total": {"$sum": 1},
                        },
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_wdyctw_questions_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.wdyctw.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": 1}}}]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_wdyctw_answers_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.wdyctw.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {"$sum": {"$size": "$answered"}},
                        }
                    }
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_techthurs_questions_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.techthurs.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": 1}}}]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_techthurs_answers_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.techthurs.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {"$sum": {"$size": "$answered"}},
                        }
                    }
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_mentalmondays_questions_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.mentalmondays.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": 1}}}]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_mentalmondays_answers_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.mentalmondays.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {"$sum": {"$size": "$answered"}},
                        }
                    }
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_tacotuesday_questions_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.taco_tuesday.aggregate(
                [{"$group": {"_id": "$guild_id", "total": {"$sum": 1}}}]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_tacotuesday_answers_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.taco_tuesday.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {"$sum": {"$size": "$answered"}},
                        }
                    }
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    # need to update data here to include guild_id
    def get_game_keys_available_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.game_keys.aggregate(
                [
                    {"$match": {"redeemed_by": {"$eq": None}}},
                    {"$group": {"_id": "$guild_id", "total": {"$sum": 1}}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    # need to update data here to include guild_id
    def get_game_keys_redeemed_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.game_keys.aggregate(
                [
                    {"$match": {"redeemed_by": {"$ne": None}}},
                    {"$group": {"_id": "$guild_id", "total": {"$sum": 1}}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    # need to update data here to include guild_id
    def get_minecraft_whitelisted_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.minecraft_users.aggregate(
                [
                    {"$match": {"whitelist": {"$eq": True}}},
                    {"$group": {"_id": "$guild_id", "total": {"$sum": 1}}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_logs(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.logs.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                # if guild_id is None, then set it to 0
                                "guild_id": {"$ifNull": ["$guild_id", 0]},
                                "level": "$level",
                            },
                            "total": {"$sum": 1},
                        },
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_team_requests_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.stream_team_requests.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {"$sum": 1},
                        },
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_birthdays_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.birthdays.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {"$sum": 1},
                        },
                    },
                ]
            )

        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_first_messages_today_count(self):
        try:
            if self.connection is None:
                self.open()
            # get UTC time for midnight today
            utc_today = datetime.datetime.combine(
                datetime.datetime.utcnow().today(), datetime.datetime.min.time()
            )
            # convert utc_today to unix timestamp
            utc_today_ts = int(
                (utc_today - datetime.datetime(1970, 1, 1)).total_seconds()
            )

            return self.connection.first_message.aggregate(
                [
                    {"$match": {"timestamp": {"$gte": utc_today_ts}}},
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {"$sum": 1},
                        },
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_messages_tracked_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.messages.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$guild_id",
                            "total": {"$sum": {"$size": "$messages"}},
                        },
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_user_messages_tracked(self):
        try:
            if self.connection is None:
                self.open()
            # get the top limit messages from users.
            # join the users collection to get the username
            # sort by count descending

            return self.connection.messages.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "guild_id": "$guild_id",
                                "user_id": "$user_id",
                            },
                            "total": {"$sum": {"$size": "$messages"}},
                        },
                    },
                    {
                        "$lookup": {
                            "from": "users",
                            "let": {
                                "user_id": "$_id.user_id",
                                "guild_id": "$_id.guild_id",
                            },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                    }
                                },
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$guild_id", "$$guild_id"]}
                                    }
                                },
                            ],
                            "as": "user",
                        }
                    },
                    {
                        "$match": {
                            "user.bot": {"$ne": True},
                            "user.system": {"$ne": True},
                            "user": {"$ne": []},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_users_by_status(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.users.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "guild_id": "$guild_id",
                                # if status is None, then set it to unknown
                                "status": {"$ifNull": ["$status", "UNKNOWN"]},
                            },
                            "total": {"$sum": 1},
                        },
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_known_users(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.users.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "guild_id": "$guild_id",
                                # if bot is true, then type is bot.
                                # if system is true, then type is system.
                                # else type is user
                                "type": {
                                    "$cond": [
                                        {"$eq": ["$bot", True]},
                                        "bot",
                                        {
                                            "$cond": [
                                                {"$eq": ["$system", True]},
                                                "system",
                                                "user",
                                            ]
                                        },
                                    ]
                                },
                            },
                            "total": {"$sum": 1},
                        },
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_top_taco_gifters(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.taco_gifts.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "user_id": "$user_id",
                                "guild_id": "$guild_id",
                            },
                            "total": {"$sum": "$count"},
                        }
                    },
                    {
                        "$lookup": {
                            "from": "users",
                            "let": {
                                "user_id": "$_id.user_id",
                                "guild_id": "$_id.guild_id",
                            },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                    }
                                },
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$guild_id", "$$guild_id"]}
                                    }
                                },
                            ],
                            "as": "user",
                        }
                    },
                    {
                        "$match": {
                            "user.bot": {"$ne": True},
                            "user.system": {"$ne": True},
                            "user": {"$ne": []},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_top_taco_reactors(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.tacos_reactions.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "user_id": "$user_id",
                                "guild_id": "$guild_id",
                            },
                            "total": {"$sum": 1},
                        }
                    },
                    {
                        "$lookup": {
                            "from": "users",
                            "let": {
                                "user_id": "$_id.user_id",
                                "guild_id": "$_id.guild_id",
                            },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                    }
                                },
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$guild_id", "$$guild_id"]}
                                    }
                                },
                            ],
                            "as": "user",
                        }
                    },
                    {
                        "$match": {
                            "user.bot": {"$ne": True},
                            "user.system": {"$ne": True},
                            "user": {"$ne": []},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_top_taco_receivers(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.tacos.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "user_id": "$user_id",
                                "guild_id": "$guild_id",
                            },
                            "total": {"$sum": "$count"},
                        }
                    },
                    {
                        "$lookup": {
                            "from": "users",
                            "let": {
                                "user_id": "$_id.user_id",
                                "guild_id": "$_id.guild_id",
                            },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                    }
                                },
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$guild_id", "$$guild_id"]}
                                    }
                                },
                            ],
                            "as": "user",
                        }
                    },
                    {
                        "$match": {
                            "user.bot": {"$ne": True},
                            "user.system": {"$ne": True},
                            "user": {"$ne": []},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_live_activity(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.live_activity.aggregate(
                [
                    {"$match": {"status": "ONLINE"}},
                    {
                        "$group": {
                            "_id": {
                                "user_id": "$user_id",
                                "guild_id": "$guild_id",
                                "platform": "$platform",
                            },
                            "total": {"$sum": 1},
                        }
                    },
                    {
                        "$lookup": {
                            "from": "users",
                            "let": {
                                "user_id": "$_id.user_id",
                                "guild_id": "$_id.guild_id",
                            },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                    }
                                },
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$guild_id", "$$guild_id"]}
                                    }
                                },
                            ],
                            "as": "user",
                        }
                    },
                    {
                        "$match": {
                            "user.bot": {"$ne": True},
                            "user.system": {"$ne": True},
                            "user": {"$ne": []},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_suggestions(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.suggestions.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "guild_id": "$guild_id",
                                "state": "$state",
                            },
                            "total": {"$sum": 1},
                        },
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_user_join_leave(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.user_join_leave.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "guild_id": "$guild_id",
                                "action": "$action",
                            },
                            "total": {"$sum": 1},
                        },
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_photo_posts_count(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.photo_posts.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "user_id": "$user_id",
                                "guild_id": "$guild_id",
                                "channel": "$channel_name",
                            },
                            "total": {"$sum": 1},
                        }
                    },
                    {
                        "$lookup": {
                            "from": "users",
                            "let": {
                                "user_id": "$_id.user_id",
                                "guild_id": "$_id.guild_id",
                            },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                    }
                                },
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$guild_id", "$$guild_id"]}
                                    }
                                },
                            ],
                            "as": "user",
                        }
                    },
                    {
                        "$match": {
                            "user.bot": {"$ne": True},
                            "user.system": {"$ne": True},
                            "user": {"$ne": []},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_taco_logs_counts(self):
        try:
            if self.connection is None:
                self.open()

            # this is the log entry docuemnt
            # {
            #     _id: ObjectId('64823bc04b3af18f34e7e2ec'),
            #     guild_id: '942532970613473293',
            #     from_user_id: '592430549277343746',
            #     to_user_id: '262031734260891648',
            #     count: 1,
            #     type: 'REACT_REWARD',
            #     reason: 'reacting to darthminos\'s message with a 🌮',
            #     timestamp: 1686256576.813649
            # }

            # aggregate all tacos_log entries for a guild, grouped by type, and sum the count
            logs = self.connection.tacos_log.aggregate(
                [
                    {
                        "$group": {
                            "_id": {"type": "$type", "guild_id": "$guild_id"},
                            "total": {"$sum": "$count"},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
            return logs
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_system_action_counts(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.system_actions.aggregate(
                [
                    {
                        "$group": {
                            "_id": {"action": "$action", "guild_id": "$guild_id"},
                            "total": {"$sum": 1},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_guilds(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.guilds.find()
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    # get trivia questions, expand the correct users and incorrect users into separate lists of user objects
    def get_trivia_questions(self) -> list:
        try:
            if self.connection is None:
                self.open()
            return list(
                self.connection.trivia_questions.aggregate(
                    [
                        {
                            "$group": {
                                "_id": {
                                    "guild_id": "$guild_id",
                                    "category": "$category",
                                    "difficulty": "$difficulty",
                                    "starter_id": "$starter_id",
                                },
                                "total": {"$sum": 1},
                            },
                        },
                        {
                            "$lookup": {
                                "from": "users",
                                "let": {
                                    "user_id": "$_id.starter_id",
                                    "guild_id": "$_id.guild_id",
                                },
                                "pipeline": [
                                    {
                                        "$match": {
                                            "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                        }
                                    },
                                    {
                                        "$match": {
                                            "$expr": {
                                                "$eq": ["$guild_id", "$$guild_id"]
                                            }
                                        }
                                    },
                                ],
                                "as": "starter",
                            }
                        },
                        {"$sort": {"timestamp": -1}},
                    ]
                )
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return []

    # TODO: this is not working
    def get_trivia_answer_status_per_user(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.trivia_questions.aggregate(
                [
                    # unwind correct and incorrect users id.
                    # look up the user document for each user id
                    # add a new field to each document to indicate if the user was correct or incorrect
                    # group by user id and count the number of correct and incorrect answers
                    # sort by total correct answers
                    {"$unwind": "$correct_users"},
                    {
                        "$lookup": {
                            "from": "users",
                            "let": {
                                "user_id": "$correct_users",
                                "guild_id": "$guild_id",
                            },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                    }
                                },
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$guild_id", "$$guild_id"]}
                                    }
                                },
                            ],
                            "as": "user",
                        }
                    },
                    {"$addFields": {"user.state": "CORRECT"}},
                    {"$unwind": "$incorrect_users"},
                    {
                        "$lookup": {
                            "from": "users",
                            "let": {
                                "user_id": "$incorrect_users",
                                "guild_id": "$guild_id",
                            },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                    }
                                },
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$guild_id", "$$guild_id"]}
                                    }
                                },
                            ],
                            "as": "user",
                        }
                    },
                    {"$addFields": {"user.state": "INCORRECT"}},
                    {"$unwind": "$user"},
                    {
                        "$group": {
                            "_id": {
                                "user_id": "$user.user_id",
                                "username": "$user.username",
                                "guild_id": "$user.guild_id",
                                "state": "$user.state",
                            },
                            "total": {"$sum": 1},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_invites_by_user(self):
        # invite model:
        # {
        #  code: 'RejCsPqBvn',
        #  guild_id: '942532970613473293',
        #  info: {
        #      id: 'RejCsPqBvn',
        #      code: 'RejCsPqBvn',
        #      inviter_id: '262031734260891648',
        #      uses: 3,
        #      max_uses: 0,
        #      max_age: 0,
        #      temporary: false,
        #      created_at: ISODate('2022-03-01T18:01:20.153Z'),
        #      revoked: null,
        #      channel_id: '948278701290840074',
        #      url: 'https://discord.gg/RejCsPqBvn'
        #  },
        #  timestamp: 1686462431.127954,
        #  invites: [
        #      {
        #          user_id: '905226717654822912',
        #          timestamp: 1646402498.029469
        #      },
        #      {
        #          user_id: '905226717654822912',
        #          timestamp: 1646402737.964417
        #      },
        #      {
        #          user_id: '905226717654822912',
        #          timestamp: 1646402924.642139
        #      }
        #  ]
        # }
        try:
            if self.connection is None:
                self.open()
            # info.inviter_id is the user who created the invite
            # info.uses is the number of times the invite was used

            return self.connection.invite_codes.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "user_id": "$info.inviter_id",
                                "guild_id": "$guild_id",
                            },
                            "total": {"$sum": "$info.uses"},
                        }
                    },
                    {
                        "$lookup": {
                            "from": "users",
                            "let": {
                                "user_id": "$_id.user_id",
                                "guild_id": "$_id.guild_id",
                            },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$user_id", "$$user_id"]}
                                    }
                                },
                                {
                                    "$match": {
                                        "$expr": {"$eq": ["$guild_id", "$$guild_id"]}
                                    }
                                },
                            ],
                            "as": "user",
                        }
                    },
                    {
                        "$match": {
                            "user.bot": {"$ne": True},
                            "user.system": {"$ne": True},
                            "user": {"$ne": []},
                        }
                    },
                    {"$sort": {"total": -1}},
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_introductions(self):
        try:
            if self.connection is None:
                self.open()
            return self.connection.introductions.aggregate(
                [
                    {
                        "$group": {
                            "_id": {"guild_id": "$guild_id", "approved": "$approved"},
                            "total": {"$sum": 1},
                        }
                    },
                ]
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
