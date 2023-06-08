from pymongo import MongoClient
from bson.objectid import ObjectId
import traceback
import json
import typing
import datetime
import pytz

import uuid

from bot.cogs.lib.minecraft_op import MinecraftOpLevel
# from discord.ext.commands.converter import CategoryChannelConverter
from . import database
from . import settings
from . import utils
from . import models

# from .mongodb import migration

class MongoDatabase(database.Database):
    def __init__(self):
        super().__init__()
        self.settings = settings.Settings()
        self.client = None
        self.connection = None
        pass

    def RESET_MIGRATION(self):
        pass
        # try:
        #     if not self.connection:
        #         self.open()
        #     print("RESET MIGRATION STATUS")
            # self.connection.create_channels.delete_many({})
            # self.connection.category_settings.delete_many({})
            # self.connection.user_settings.delete_many({})
            # self.connection.text_channels.delete_many({})
            # self.connection.voice_channels.delete_many({})
            # self.connection.migration.delete_many({})
        #     print("ALL DATA PURGED")
        # except Exception as ex:
        #     print(ex)
        #     traceback.print_exc()
        # finally:
        #     if self.connection:
        #         self.close()

    def UPDATE_SCHEMA(self, newDBVersion: int):
        pass
        # print(f"[mongo.UPDATE_SCHEMA] INITIALIZE MONGO")
        # try:
        #     # check if migrated
        #     # if not, open sqlitedb and migate the data
        #     if not self.connection:
        #         self.open()

        #     migrator = migration.MongoMigration(newDBVersion)
        #     migrator.run()

        #     # setup missing guild category settings...
        #     guild_channels = self.connection.create_channels.find({}, { "guildID": 1, "voiceChannelID": 1, "voiceCategoryID": 1 })
        #     for g in guild_channels:
        #         gcs = self.get_guild_category_settings(guildId=g['guildID'], categoryId=g['voiceCategoryID'])
        #         if not gcs:
        #             print(f"[UPDATE_SCHEMA] Inserting Default Category Settings for guild: {g['guildID']} category: {g['voiceCategoryID']}")
        #             guild_setting = self.get_guild_settings(g['guildID'])
        #             if guild_setting:
        #                 self.set_guild_category_settings(guildId=g['guildID'], categoryId=g['voiceCategoryID'], channelLimit=0, channelLocked=False, bitrate=64, defaultRole=guild_setting.default_role)
        #             else:
        #                 self.set_guild_category_settings(guildId=g['guildID'], categoryId=g['voiceCategoryID'], channelLimit=0, channelLocked=False, bitrate=64, defaultRole="@everyone")

        # except Exception as ex:
        #     print(ex)
        #     traceback.print_exc()
        # finally:
        #     if self.connection:
        #         self.close()


    def open(self):
        if not self.settings.db_url:
            raise ValueError("MONGODB_URL is not set")
        self.client = MongoClient(self.settings.db_url)
        self.connection = self.client.tacobot
    def close(self):
        try:
            if self.client:
                self.client.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def insert_log(self, guildId: int, level: str, method: str, message: str, stackTrace: str = None):
        try:
            if self.connection is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "timestamp": utils.get_timestamp(),
                "level": level.name,
                "method": method,
                "message": message,
                "stack_trace": stackTrace
            }
            self.connection.logs.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def clear_log(self, guildId):
        try:
            if self.connection is None:
                self.open()
            self.connection.logs.delete_many({ "guild_id": guildId })
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def add_twitchbot_to_channel(self, guildId: int, twitch_channel: str):
        try:
            if self.connection is None:
                self.open()
            twitch_channel = utils.clean_channel_name(twitch_channel)

            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "channel": twitch_channel,
                "timestamp": timestamp,
            }
            self.connection.twitch_channels.update_one({"guild_id": self.settings.discord_guild_id, "channel": twitch_channel}, {"$set": payload}, upsert=True)
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex
        finally:
            self.close()

    def add_stream_team_request(self, guildId: int, userName: str, userId: int, twitchName: str = None):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "user_name": userName,
                "twitch_name": twitchName,
                "timestamp": timestamp
            }
            # if not in table, insert
            if not self.connection.stream_team_requests.find_one(payload):
                self.connection.stream_team_requests.insert_one(payload)
            else:
                print(f"[DEBUG] [mongo.add_stream_team_request] [guild:0] User {userName}, already in table")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def remove_stream_team_request(self, guildId: int, userId: int):
        try:
            if self.connection is None:
                self.open()
            self.connection.stream_team_requests.delete_many({ "guild_id": str(guildId), "user_id": userId })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_stream_team_requests(self, guildId: int):
        pass

    def set_user_twitch_info(self, userId: int, twitchId: str, twitchName: str):
        try:
            if self.connection is None:
                self.open()
            payload = {
                "user_id": str(userId),
                "twitch_id": twitchId,
                "twitch_name": twitchName
            }
            # insert or update user twitch info
            self.connection.twitch_user.update_one({ "user_id": str(userId) }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_user_twitch_info(self, userId: int):
        try:
            if self.connection is None:
                self.open()
            return self.connection.twitch_user.find_one({ "user_id": str(userId) })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    # Tacos
    def remove_all_tacos(self, guildId: int, userId: int):
        try:
            if self.connection is None:
                self.open()
            print(f"[DEBUG] [mongo.remove_all_tacos] [guild:0] Removing tacos for user {userId}")
            self.connection.tacos.delete_many({ "guild_id": str(guildId), "user_id": str(userId) })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def add_tacos(self, guildId: int, userId: int, count: int):
        try:
            if self.connection is None:
                self.open()

            user_tacos = self.get_tacos_count(guildId, userId)
            if user_tacos is None:
                print(f"[DEBUG] [mongo.add_tacos] [guild:0] User {userId} not in table")
                user_tacos = 0
            else:
                user_tacos = user_tacos or 0
                print(f"[DEBUG] [mongo.add_tacos] [guild:0] User {userId} has {user_tacos} tacos")

            user_tacos += count
            print(f"[DEBUG] [mongo.add_tacos] [guild:0] User {userId} now has {user_tacos} tacos")
            self.connection.tacos.update_one({ "guild_id": str(guildId), "user_id": str(userId) }, { "$set": { "count": user_tacos } }, upsert=True)
            return user_tacos
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def remove_tacos(self, guildId: int, userId: int, count: int):
        try:
            if count < 0:
                print(f"[DEBUG] [mongo.remove_tacos] [guild:0] Count is less than 0")
                return 0
            if self.connection is None:
                self.open()

            user_tacos = self.get_tacos_count(guildId, userId)
            if user_tacos is None:
                print(f"[DEBUG] [mongo.remove_tacos] [guild:0] User {userId} not in table")
                user_tacos = 0
            else:
                user_tacos = user_tacos or 0
                print(f"[DEBUG] [mongo.remove_tacos] [guild:0] User {userId} has {user_tacos} tacos")

            user_tacos -= count
            if user_tacos < 0:
                user_tacos = 0

            print(f"[DEBUG] [mongo.remove_tacos] [guild:0] User {userId} now has {user_tacos} tacos")
            self.connection.tacos.update_one({ "guild_id": str(guildId), "user_id": str(userId) }, { "$set": { "count": user_tacos } }, upsert=True)
            return user_tacos
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_tacos_count(self, guildId: int, userId: int):
        try:
            if self.connection is None:
                self.open()
            data = self.connection.tacos.find_one({ "guild_id": str(guildId), "user_id": str(userId) })
            if data is None:
                print(f"[DEBUG] [mongo.get_tacos_count] [guild:{guildId}] User {userId} not in table")
                return None
            return data['count']
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
        pass
    def get_total_gifted_tacos(self, guildId: int, userId: int, timespan_seconds: int = 86400):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            data = self.connection.taco_gifts.find({ "guild_id": str(guildId), "user_id": str(userId), "timestamp": { "$gt": timestamp - timespan_seconds } })
            if data is None:
                return 0
            # add up all the gifts from the count column
            total_gifts = 0
            for gift in data:
                total_gifts += gift['count']
            return total_gifts
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def add_taco_gift(self, guildId: int, userId: int, count: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "count": count,
                "timestamp": timestamp
            }
            # total_gifts = self.get_total_gifted_tacos(guildId, userId, 86400)

            # add the gift
            self.connection.taco_gifts.insert_one( payload )
            return True

        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return False
        finally:
            if self.connection:
                self.close()

    def add_taco_reaction(self, guildId: int, userId: int, channelId: int, messageId: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "timestamp": timestamp
            }
            # log entry for the user
            print(f"[DEBUG] [mongo.add_taco_reaction] [guild:0] Adding taco reaction for user {userId}")
            self.connection.tacos_reactions.update_one({ "guild_id": str(guildId), "user_id": str(userId), "timestamp": timestamp }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_taco_reaction(self, guildId: int, userId: int, channelId: int, messageId: int):
        try:
            if self.connection is None:
                self.open()
            reaction = self.connection.tacos_reactions.find_one({ "guild_id": str(guildId), "user_id": str(userId), "channel_id": str(channelId), "message_id": str(messageId) })
            if reaction is None:
                return None
            return reaction
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def add_suggestion_create_message(self, guildId: int, channelId: int, messageId: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "timestamp": timestamp
            }
            # log entry for the user
            print(f"[DEBUG] [mongo.add_suggestion_create_message] [guild:0] Adding suggestion create message for guild {guildId}")
            self.connection.suggestion_create_messages.update_one({ "guild_id": str(guildId), "channel_id": str(channelId), "message_id": messageId }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def remove_suggestion_create_message(self, guildId: int, channelId: int, messageId: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            self.connection.suggestion_create_messages.delete_one({ "guild_id": str(guildId), "channel_id": str(channelId), "message_id": str(messageId), "timestamp": timestamp })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def add_settings(self, guildId: int, name:str, settings: dict):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "name": name,
                "settings": settings,
                "timestamp": timestamp
            }
            # insert the settings for the guild in to the database with key name and timestamp
            self.connection.settings.update_one({ "guild_id": str(guildId), "name": name }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_settings(self, guildId: int, name:str):
        try:
            if self.connection is None:
                self.open()
            settings = self.connection.settings.find_one({ "guild_id": str(guildId), "name": name })
            # explicitly return None if no settings are found
            if settings is None:
                return None
            # return the settings object
            return settings['settings']
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_suggestion(self, guildId: int, messageId: int):
        try:
            if self.connection is None:
                self.open()
            suggestion = self.connection.suggestions.find_one({ "guild_id": str(guildId), "message_id": str(messageId) })
            # explicitly return None if no suggestion is found
            if suggestion is None:
                return None
            # return the suggestion object
            return suggestion
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_suggestion_by_id(self, guildId: int, suggestionId: str):
        try:
            if self.connection is None:
                self.open()
            suggestion = self.connection.suggestions.find_one({ "guild_id": str(guildId), "id": str(suggestionId) })
            # explicitly return None if no suggestion is found
            if suggestion is None:
                return None
            # return the suggestion object
            return suggestion
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def set_state_suggestion_by_id(self, guildId: int, suggestionId: str, state: str, userId: int, reason: str):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "id": suggestionId,
                "state": state.upper().strip()
            }
            # insert the suggestion into the database
            action_payload = {
                "state": state.upper().strip(),
                "user_id": str(userId),
                "reason": reason,
                "timestamp": timestamp
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one({ "guild_id": str(guildId), "id": str(suggestionId) }, { "$set": payload, "$push": { "actions" : action_payload } }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def set_state_suggestion(self, guildId: int, messageId: int, state: str, userId: int, reason: str):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "message_id": str(messageId),
                "state": state.upper().strip(),
            }
            action_payload = {
                "state": state.upper().strip(),
                "user_id": str(userId),
                "reason": reason,
                "timestamp": timestamp
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one({ "guild_id": str(guildId), "message_id": str(messageId) }, { "$set": payload, "$push": { "actions" : action_payload } }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def has_user_voted(self, suggestionId: str, userId: int):
        try:
            if self.connection is None:
                self.open()
            suggestion = self.connection.suggestions.find_one({ "id": str(suggestionId) })
            if suggestion is None:
                return False
            if suggestion['votes'] is None:
                return False
            if str(userId) in [ v['user_id'] for v in suggestion['votes'] ]:
                return True
            return False
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def unvote_suggestion_by_id(self, guildId: int, suggestionId: str, userId: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "id": suggestionId,
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one({ "guild_id": str(guildId), "id": str(suggestionId) }, { "$pull": { "votes": { "user_id": str(userId) } } }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def unvote_suggestion(self, guildId: int, messageId: int, userId: int ):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "message_id": str(messageId),
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one({ "guild_id": str(guildId), "message_id": str(messageId) }, { "$pull": { "votes": { "user_id": str(userId) } } }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_suggestion_votes_by_id(self, suggestionId: str):
        try:
            if self.connection is None:
                self.open()
            suggestion = self.connection.suggestions.find_one({ "id": str(suggestionId) })
            if suggestion is None:
                return None
            return suggestion['votes']
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def vote_suggestion(self, guildId: int, messageId: int, userId: int, vote: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            vote = vote if vote in [1, -1] else 0
            payload = {
                "user_id": userId,
                "vote": vote,
                "timestamp": timestamp
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one({ "guild_id": str(guildId), "message_id": str(messageId)}, { "$push": { "votes": payload } }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def vote_suggestion_by_id(self, suggestionId: str, userId: int, vote: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            vote = vote if vote in [1, -1] else 0
            payload = {
                "user_id": str(userId),
                "vote": vote,
                "timestamp": timestamp
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one({ "id": suggestionId }, { "$push": { "votes": payload } }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def add_suggestion(self, guildId: int, messageId: int, suggestion: dict):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            suggestion_data = utils.dict_get(suggestion, "suggestion", {})
            payload = {
                "id": utils.dict_get(suggestion,'id', uuid.uuid4().hex),
                "guild_id": str(guildId),
                "author_id": str(utils.dict_get(suggestion, "author_id", None)),
                "message_id": str(messageId),
                "actions": [],
                "votes": [],
                "suggestion": suggestion_data,
                "state": utils.dict_get(suggestion,'state', 'ACTIVE').upper().strip(),
                "timestamp": timestamp
            }
            # insert the suggestion for the guild in to the database with key name and timestamp
            self.connection.suggestions.insert_one( payload )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def delete_suggestion_by_id(self, guildId: int, suggestionId: str, userId: int, reason: str):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            states = models.SuggestionStates()
            state = states.DELETED
            payload = {
                "guild_id": str(guildId),
                "id": suggestionId,
            }
            action_payload = {
                "state": state.upper().strip(),
                "user_id": str(userId),
                "reason": reason,
                "timestamp": timestamp
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one({ "guild_id": str(guildId), "id": str(suggestionId) }, { "$set": { "state": state }, "$push": { "actions": action_payload } }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_wait_invoke(self, guildId: int, channelId: int, messageId: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "timestamp": timestamp
            }
            self.connection.wait_invokes.update_one({ "guild_id": str(guildId), "channel_id": str(channelId), "message_id": str(messageId) }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def untrack_wait_invoke(self, guildId: int, channelId: int, messageId: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "timestamp": timestamp
            }
            self.connection.wait_invokes.delete_one({ "guild_id": str(guildId), "channel_id": str(channelId), "message_id": str(messageId) })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_wait_invokes(self, guildId: int, channelId: int):
        try:
            if self.connection is None:
                self.open()
            return self.connection.wait_invokes.find({ "guild_id": str(guildId), "channel_id": str(channelId) })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_invite_code(self, guildId: int, inviteCode: str, inviteInfo: dict, userInvite: dict):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "code": inviteCode,
                "info": inviteInfo,
                "timestamp": timestamp
            }
            if userInvite is None:
                self.connection.invite_codes.update_one({ "guild_id": str(guildId), "code": inviteCode }, { "$set": payload }, upsert=True)
            else:
                self.connection.invite_codes.update_one({ "guild_id": str(guildId), "code": inviteCode }, { "$set": payload, "$push": { "invites": userInvite }  }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_invite_code(self, guildId: int, inviteCode: str):
        try:
            if self.connection is None:
                self.open()
            return self.connection.invite_codes.find_one({ "guild_id": str(guildId), "code": inviteCode })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_live_activity(self, guildId: int, userId: int, live: bool, platform: str, url: str):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "status": "ONLINE" if live else "OFFLINE",
                "platform": platform.upper().strip(),
                "url": url,
                "timestamp": timestamp
            }
            self.connection.live_activity.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()


    def track_live(self, guildId: int, userId: int, platform: str, channelId: int = None, messageId: int = None, url: str = None):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "platform": platform.upper().strip(),
                "url": url,
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "timestamp": timestamp
            }
            self.connection.live_tracked.update_one({ "guild_id": str(guildId), "user_id": str(userId), "platform": platform.upper().strip()}, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_tracked_live(self, guildId: int, userId: int, platform: str):
        try:
            if self.connection is None:
                self.open()
            return self.connection.live_tracked.find({ "guild_id": str(guildId), "user_id": str(userId), "platform": platform.upper().strip() })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_tracked_live_by_url(self, guildId: int, url: str):
        try:
            if self.connection is None:
                self.open()
            return self.connection.live_tracked.find({ "guild_id": str(guildId), "url": url })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_tracked_live_by_user(self, guildId: int, userId: int):
        try:
            if self.connection is None:
                self.open()
            return self.connection.live_tracked.find({ "guild_id": str(guildId), "user_id": str(userId) })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def untrack_live(self, guildId: int, userId: int, platform: str):
        try:
            if self.connection is None:
                self.open()
            self.connection.live_tracked.delete_one({ "guild_id": str(guildId),  "user_id": str(userId), "platform": platform.upper().strip() })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def add_user_birthday(self, guildId: int, userId: int, month: int, day: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "month": month,
                "day": day,
                "timestamp": timestamp
            }
            self.connection.birthdays.update_one( { "guild_id": str(guildId), "user_id": str(userId) }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_user_birthday(self, guildId: int, userId: int):
        try:
            if self.connection is None:
                self.open()
            return self.connection.birthdays.find_one({ "guild_id": str(guildId), "user_id": str(userId) })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_user_birthdays(self, guildId: int, month: int, day: int):
        try:
            if self.connection is None:
                self.open()
            return self.connection.birthdays.find({ "guild_id": str(guildId), "month": month, "day": day })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def track_birthday_check(self, guildId: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "timestamp": timestamp
            }
            self.connection.birthday_checks.update_one({ "guild_id": str(guildId) }, { "$set": payload}, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def birthday_was_checked_today(self, guildId: int):
        try:
            if self.connection is None:
                self.open()
            checks = self.connection.birthday_checks.find({ "guild_id": str(guildId) })
            if checks.count() > 0:
                # central_tz= pytz.timezone(self.settings.timezone)
                date = datetime.datetime.utcnow().date()
                start = datetime.datetime.combine(date, datetime.time.min)
                end = datetime.datetime.combine(date, datetime.time.max)
                start_ts = utils.to_timestamp(datetime.datetime.combine(date, datetime.time.min))
                end_ts = utils.to_timestamp(datetime.datetime.combine(date, datetime.time.max))
                timestamp = checks[0]["timestamp"]

                # ts_date = utils.from_timestamp(timestamp)
                # cst_dt = ts_date.replace(tzinfo=central_tz)
                # cst_ts = utils.to_timestamp(cst_dt, tz=central_tz)
                # cst_start = start.replace(tzinfo=central_tz)
                # cst_end = end.replace(tzinfo=central_tz)
                # cst_start_ts = utils.to_timestamp(cst_start, tz=central_tz)
                # cst_end_ts = utils.to_timestamp(cst_end, tz=central_tz)

                if timestamp >= start_ts and timestamp <= end_ts:
                    return True

                # if cst_ts >= cst_start_ts and cst_ts <= cst_end_ts:
                #     return True
            return False
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def save_tqotd(self, guildId: int, question: str, author: int):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "question": question,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp
            }
            self.connection.tqotd.update_one({ "guild_id": str(guildId), "timestamp": timestamp }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def track_tqotd_answer(self, guildId: int, userId: int, message_id: int):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())
            result = self.connection.tqotd.find_one(
                {"guild_id": str(guildId), "timestamp": timestamp}
            )

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            if result:
                self.connection.tqotd.update_one({ "guild_id": str(guildId), "timestamp": timestamp }, { "$push": { "answered": { "user_id": str(userId), "message_id": messageId, "timestamp": ts_track } } }, upsert=True)
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.tqotd.find_one(
                    {"guild_id": str(guildId), "timestamp": timestamp}
                )
                if result:
                    self.connection.tqotd.update_one({ "guild_id": str(guildId), "timestamp": timestamp }, { "$push": { "answered": { "user_id": str(userId), "message_id": messageId, "timestamp": ts_track } } }, upsert=True)
                else:
                    raise Exception(f"No TQOTD found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def tqotd_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the TQOTD?
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.tqotd.find_one(
                {"guild_id": str(guildId), "timestamp": timestamp}
            )
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.tqotd.find_one(
                    {"guild_id": str(guildId), "timestamp": timestamp}
                )
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No TQOTD found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex
        finally:
            if self.connection:
                self.close()
    def _get_twitch_name(self, userId: int):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.twitch_names.find_one({ "user_id": str(userId) })
            if result:
                return result["twitch_name"]
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def set_twitch_discord_link_code(self, userId: int, code: str):
        try:
            if self.connection is None:
                self.open()
            twitch_name = self._get_twitch_name(userId)
            if not twitch_name:
                payload = {
                    "user_id": str(userId),
                    "link_code": code.strip()
                }
                self.connection.twitch_user.update_one( { "user_id": str(userId) }, { "$set": payload }, upsert=True )
                return True
            else:
                raise ValueError(f"Twitch user {twitch_name} already linked")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex
        finally:
            self.close()

    def link_twitch_to_discord_from_code(self, userId: int, code: str):
        try:
            if self.connection is None:
                self.open()
            twitch_name = self._get_twitch_name(userId)
            if not twitch_name:
                result = self.connection.twitch_user.find_one({ "link_code": code.strip() } )
                if result:
                    payload = {
                        "user_id": str(userId),
                    }
                    self.connection.twitch_user.update_one( { "link_code": code.strip() }, { "$set": payload }, upsert=True )
                    return True
                else:
                    raise ValueError(f"Unable to find an entry for a user with link code: {code}")
            else:
                raise ValueError(f"Twitch user {twitch_name} already linked")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex
        finally:
            self.close()

    def get_minecraft_user(self, userId: int):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.minecraft_users.find_one({ "user_id": str(userId) })
            if result:
                return result
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def whitelist_minecraft_user(self, userId: int, username: str, uuid: str, whitelist: bool = True):
        try:
            if self.connection is None:
                self.open()
            payload = {
                "user_id": str(userId),
                "username": username,
                "uuid": uuid,
                "whitelist": whitelist
            }
            self.connection.minecraft_users.update_one( { "user_id": str(userId) }, { "$set": payload }, upsert=True )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def op_minecraft_user(self, userId: int, username: str, uuid: str, op: bool = True, level: MinecraftOpLevel = MinecraftOpLevel.LEVEL1, bypassPlayerCount: bool = False):
        try:
            if self.connection is None:
                self.open()
            payload = {
                "user_id": str(userId),
                "username": username,
                "uuid": uuid,
                "op": {
                    "enabled": op,
                    "level": int(level),
                    "bypassesPlayerLimit": bypassPlayerCount
                }
            }
            self.connection.minecraft_users.update_one( { "user_id": str(userId) }, { "$set": payload }, upsert=True )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def find_open_game_key_offer(self, guild_id: int, channel_id: int):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.game_key_offers.find_one({ "guild_id": str(guild_id), "channel_id": str(channel_id) })
            if result:
                return result
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def open_game_key_offer(self, game_key_id: str, guild_id: int, message_id:int, channel_id: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guild_id),
                "game_key_id": str(game_key_id),
                "message_id": str(message_id),
                "channel_id": str(channel_id),
                "timestamp": timestamp
            }
            self.connection.game_key_offers.update_one( { "guild_id": str(guild_id), "game_key_id": game_key_id }, { "$set": payload }, upsert=True )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def close_game_key_offer_by_message(self, guild_id: int, message_id: int):
        try:
            if self.connection is None:
                self.open()
            self.connection.game_key_offers.delete_one({ "guild_id": str(guild_id), "message_id": str(message_id) })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def close_game_key_offer(self, guild_id: int, game_key_id: str):
        try:
            if self.connection is None:
                self.open()
            self.connection.game_key_offers.delete_one({ "guild_id": str(guild_id), "game_key_id": game_key_id })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def claim_game_key_offer(self, game_key_id: str, user_id: int):
        try:
            if self.connection is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "redeemed_by": str(user_id),
                "redeemed_timestamp": timestamp
            }
            self.connection.game_keys.update_one( { "_id": ObjectId(game_key_id) }, { "$set": payload }, upsert=True )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex
        finally:
            if self.connection:
                self.close()

    def get_game_key_data(self, game_key_id: str):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.game_keys.find_one({ "_id": ObjectId(game_key_id) })
            if result:
                return result
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def get_random_game_key_data(self):
        try:
            if self.connection is None:
                self.open()
            result = self.connection.game_keys.aggregate([
                { "$match": { "redeemed_by": None } },
                { "$sample": { "size": 1 } }
            ])
            records = list(result)
            if records and len(records) > 0:
                record = records[0]
                return {
                    "id": record["_id"],
                    "title": record["title"],
                    "platform": record["type"],
                    "info_url": record["info_link"] or "",
                    "offered_by": record["user_owner"],
                }
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_wdyctw_answer(self, guild_id: int, user_id: int, message_id: int):
        try:
            if self.connection is None:
                self.open()

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.wdyctw.find_one(
                {"guild_id": str(guild_id), "timestamp": timestamp}
            )

            if result:
                self.connection.wdyctw.update_one({ "guild_id": str(guild_id), "timestamp": timestamp }, { "$push": { "answered": { "user_id": str(user_id), "message_id": messageId, "timestamp": ts_track } } }, upsert=True)
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.wdyctw.find_one(
                    {"guild_id": str(guild_id), "timestamp": {
                        "$gte": utils.to_timestamp(ts_back_date),
                        "$lte": utils.to_timestamp(ts_now_date)
                    }}
                )
                if result:
                    self.connection.wdyctw.update_one({ "guild_id": str(guild_id), "timestamp": result['timestamp'] }, { "$push": { "answered": { "user_id": str(user_id), "message_id": messageId, "timestamp": ts_track } } }, upsert=True)
                else:
                    raise Exception(f"No WDYCTW found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def save_wdyctw(self, guildId: int, message: str, image: str, author: int, channel_id: int = None, message_id: int = None):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id)
            }
            self.connection.wdyctw.update_one({ "guild_id": str(guildId), "timestamp": timestamp }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def wdyctw_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the WDYCTW?
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.wdyctw.find_one(
                {"guild_id": str(guildId), "timestamp": timestamp}
            )
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.wdyctw.find_one(
                    {"guild_id": str(guildId), "timestamp": timestamp}
                )
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No WDYCTW found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex
        finally:
            if self.connection:
                self.close()

    def track_techthurs_answer(self, guild_id: int, user_id: int, message_id: int):
        try:
            if self.connection is None:
                self.open()

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.techthurs.find_one(
                {"guild_id": str(guild_id), "timestamp": timestamp}
            )

            if result:
                self.connection.techthurs.update_one({ "guild_id": str(guild_id), "timestamp": timestamp }, { "$push": { "answered": { "user_id": str(user_id), "message_id": messageId, "timestamp": ts_track } } }, upsert=True)
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.techthurs.find_one(
                    {"guild_id": str(guild_id), "timestamp": {
                        "$gte": utils.to_timestamp(ts_back_date),
                        "$lte": utils.to_timestamp(ts_now_date)
                    }}
                )
                if result:
                    self.connection.techthurs.update_one({ "guild_id": str(guild_id), "timestamp": result['timestamp'] }, { "$push": { "answered": { "user_id": str(user_id), "message_id": messageId, "timestamp": ts_track } } }, upsert=True)
                else:
                    raise Exception(f"No techthurs found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def save_techthurs(self, guildId: int, message: str, image: str, author: int, channel_id: int = None, message_id: int = None):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id)
            }
            self.connection.techthurs.update_one({ "guild_id": str(guildId), "timestamp": timestamp }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def techthurs_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the techthurs?
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.techthurs.find_one(
                {"guild_id": str(guildId), "timestamp": timestamp}
            )
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.techthurs.find_one(
                    {"guild_id": str(guildId), "timestamp": timestamp}
                )
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No techthurs found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex
        finally:
            if self.connection:
                self.close()

    def track_mentalmondays_answer(self, guild_id: int, user_id: int, message_id: int):
        try:
            if self.connection is None:
                self.open()

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.mentalmondays.find_one(
                {"guild_id": str(guild_id), "timestamp": timestamp}
            )

            if result:
                self.connection.mentalmondays.update_one({ "guild_id": str(guild_id), "timestamp": timestamp }, { "$push": { "answered": { "user_id": str(user_id), "message_id": messageId, "timestamp": ts_track } } }, upsert=True)
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.mentalmondays.find_one(
                    {"guild_id": str(guild_id), "timestamp": {
                        "$gte": utils.to_timestamp(ts_back_date),
                        "$lte": utils.to_timestamp(ts_now_date)
                    }}
                )
                if result:
                    self.connection.mentalmondays.update_one({ "guild_id": str(guild_id), "timestamp": result['timestamp'] }, { "$push": { "answered": { "user_id": str(user_id), "message_id": messageId, "timestamp": ts_track } } }, upsert=True)
                else:
                    raise Exception(f"No mentalmondays found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def save_mentalmondays(self, guildId: int, message: str, image: str, author: int, channel_id: int = None, message_id: int = None):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id)
            }
            self.connection.mentalmondays.update_one({ "guild_id": str(guildId), "timestamp": timestamp }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def mentalmondays_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the mentalmondays?
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.mentalmondays.find_one(
                {"guild_id": str(guildId), "timestamp": timestamp}
            )
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.mentalmondays.find_one(
                    {"guild_id": str(guildId), "timestamp": timestamp}
                )
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No mentalmondays found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex
        finally:
            if self.connection:
                self.close()

    def save_taco_tuesday(self, guildId: int, message: str, image: str, author: int, channel_id: int = None, message_id: int = None):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id)
            }
            self.connection.taco_tuesday.update_one({ "guild_id": str(guildId), "timestamp": timestamp }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_taco_tuesday(self, guild_id: int, user_id: int):
        try:
            if self.connection is None:
                self.open()

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.taco_tuesday.find_one(
                {"guild_id": str(guild_id), "timestamp": timestamp}
            )

            if result:
                self.connection.taco_tuesday.update_one({ "guild_id": str(guild_id), "timestamp": timestamp }, { "$push": { "answered": { "user_id": str(user_id), "timestamp": ts_track } } }, upsert=True)
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.taco_tuesday.find_one(
                    {"guild_id": str(guild_id), "timestamp": {
                        "$gte": utils.to_timestamp(ts_back_date),
                        "$lte": utils.to_timestamp(ts_now_date)
                    }}
                )
                if result:
                    self.connection.taco_tuesday.update_one({ "guild_id": str(guild_id), "timestamp": result['timestamp'] }, { "$push": { "answered": { "user_id": str(user_id), "timestamp": ts_track } } }, upsert=True)
                else:
                    raise Exception(f"No taco tuesday found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def taco_tuesday_user_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the WDYCTW?
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.taco_tuesday.find_one(
                {"guild_id": str(guildId), "timestamp": timestamp}
            )
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.taco_tuesday.find_one(
                    {"guild_id": str(guildId), "timestamp": timestamp}
                )
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId):
                            return True
                    return False
                else:
                    raise Exception(f"No Taco Tuesday found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex
        finally:
            if self.connection:
                self.close()

    def track_first_message(self, guildId: int, userId: int, channelId: int, messageId: int):
        try:

            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "user_id": str(userId),
                "timestamp": timestamp
            }

            # if self.is_first_message_today(guildId=guildId, userId=userId):
            self.connection.first_message.update_one({ "guild_id": str(guildId), "user_id": str(userId), "timestamp": timestamp }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_message(self, guildId: int, userId: int, channelId: int, messageId: int):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId)
            }

            result = self.connection.messages.find_one( { "guild_id": str(guildId), "user_id": str(userId) } )
            if result:
                self.connection.messages.update_one({ "guild_id": str(guildId), "user_id": str(userId) }, { "$push": { "messages": { "channel_id": str(channelId), "message_id": str(messageId), "timestamp": timestamp } } }, upsert=True)
            else:
                self.connection.messages.insert_one({ **payload, "messages": [{ "channel_id": str(channelId), "message_id": str(messageId), "timestamp": timestamp }] })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def is_first_message_today(self, guildId: int, userId: int):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.first_message.find_one( { "guild_id": str(guildId), "user_id": str(userId), "timestamp": timestamp } )
            if result:
                return False
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_user(self, guildId: int, userId: int, username: str, discriminator: str, avatar: str, displayname: str, created: datetime.datetime = None, bot: bool = False, system: bool = False):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            created_timestamp = utils.to_timestamp(created) if created else None
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "username": username,
                "discriminator": discriminator,
                "avatar": avatar,
                "displayname": displayname,
                "created": created_timestamp,
                "bot": bot,
                "system": system,
                "timestamp": timestamp
            }

            self.connection.users.update_one({ "guild_id": str(guildId), "user_id": str(userId) }, { "$set": payload }, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_food_post(self, guildId: int, userId: int, channelId: int, messageId: int, message: str, image: str):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "message": message,
                "image": image,
                "timestamp": timestamp
            }

            self.connection.food_posts.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_user_join_leave(self, guildId: int, userId: int, join: bool):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "action": "JOIN" if join else "LEAVE",
                "timestamp": timestamp
            }

            self.connection.user_join_leave.insert_one(payload)

        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def track_tacos_log(self, guildId: int, fromUserId: int, toUserId: int, count: int, type: str, reason: str):
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guildId),
                "from_user_id": str(fromUserId),
                "to_user_id": str(toUserId),
                "count": count,
                "type": type,
                "reason": reason,
                "timestamp": timestamp
            }

            self.connection.tacos_log.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
