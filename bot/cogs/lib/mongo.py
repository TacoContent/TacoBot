from pymongo import MongoClient
import traceback
import json

# from discord.ext.commands.converter import CategoryChannelConverter
from . import database
from . import settings
from . import utils
# from .mongodb import migration

class MongoDatabase(database.Database):
    def __init__(self):
        super().__init__()
        print(f"[DEBUG] [mongo.__init__] [guild:0] INITIALIZE MONGO")
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
        print(f"[DEBUG] [mongo.open] [guild:0] Connected to MongoDB")
    def close(self):
        try:
            if self.client:
                self.client.close()
                print(f"[DEBUG] [mongo.close] [guild:0] Disconnected from MongoDB")
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

    def add_stream_team_member(self, guildId: int, teamName: str, userId: int, discordUsername: str, twitchUsername: str):
        try:
            if self.connection is None:
                print("[DEBUG] [mongo.add_stream_team_member] [guild:0] Connecting to MongoDB")
                self.open()
            payload = {
                "guild_id": str(guildId),
                "team_name": teamName.lower(),
                "user_id": str(userId),
                "discord_username": discordUsername,
                "twitch_username": twitchUsername.lower()
            }
            # if not in table, insert
            if not self.connection.stream_team_members.find_one(payload):
                self.connection.stream_team_members.insert_one(payload)
            else:
                print(f"[DEBUG] [mongo.add_stream_team_member] [guild:0] User {discordUsername}, already in table")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()

    def get_stream_team_members(self, guildId: int, teamName: str):
        try:
            if self.connection is None:
                self.open()
            return self.connection.stream_team_members.find({ "guild_id": str(guildId), "team_name": teamName.lower() })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def update_stream_team_member(self, guildId: int, userId: int, twitchUsername: str):
        try:
            if self.connection is None:
                self.open()
            self.connection.stream_team_members.update_many({ "guild_id": str(guildId), "user_id": str(userId) }, { "$set": { "twitch_username": twitchUsername.lower() } })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
    def remove_stream_team_member(self, guildId: int, teamName: str, userId: int):
        try:
            if self.connection is None:
                self.open()
            self.connection.stream_team_members.delete_many({ "guild_id": str(guildId), "team_name": teamName.lower(), "user_id": userId })
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.close()
