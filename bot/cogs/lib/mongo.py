from email import message
from tkinter.messagebox import NO
from pymongo import MongoClient
import traceback
import json
import typing
import datetime
import uuid
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
                "guild_id": guildId,
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

    def add_stream_team_request(self, guildId: int, userName: str, userId: int):
        try:
            if self.connection is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "username": userName
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
            if count < 0:
                print(f"[DEBUG] [mongo.add_tacos] [guild:0] Count is less than 0")
                return 0
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
