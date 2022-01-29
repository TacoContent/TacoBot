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
        pass
        # if not self.settings.db_url:
        #     raise ValueError("VCB_MONGODB_URL is not set")
        # self.client = MongoClient(self.settings.db_url)
        # self.connection = self.client.voicecreate
    def close(self):
        pass
        # try:
        #     if self.client:
        #         self.client.close()
        # except Exception as ex:
        #     print(ex)
        #     traceback.print_exc()

    def insert_log(self, guildId: int, level: str, method: str, message: str, stackTrace: str = None):
        pass
        # try:
        #     if self.connection is None:
        #         self.open()
        #     payload = {
        #         "guild_id": guildId,
        #         "timestamp": utils.get_timestamp(),
        #         "level": level.name,
        #         "method": method,
        #         "message": message,
        #         "stack_trace": stackTrace
        #     }
        #     self.connection.logs.insert_one(payload)
        # except Exception as ex:
        #     print(ex)
        #     traceback.print_exc()
    def clear_log(self, guildId):
        pass
        # try:
        #     if self.connection is None:
        #         self.open()
        #     self.connection.logs.delete_many({ "guild_id": guildId })
        # except Exception as ex:
        #     print(ex)
        #     traceback.print_exc()
