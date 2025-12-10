
import inspect
import typing

import requests

from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry
from bot.lib.mongodb.minecraft import MinecraftDatabase


class WhitelistManager:

    def __init__(self, minecraft_db: MinecraftDatabase):
        self.minecraft_db = minecraft_db

    def get_minecraft_user(self, guild_id: int, user_id: int) -> typing.Optional[MinecraftUserEntry]:
        # get the minecraft user entry from the database
        return self.minecraft_db.get_minecraft_user(guild_id=guild_id, user_id=user_id)

    def get_whitelist_status(self, guild_id: int, user_id: int) -> bool:
        # get the whitelist status for a user
        minecraft_user = self.get_minecraft_user(guild_id=guild_id, user_id=user_id)
        if not minecraft_user:
            return False

        return minecraft_user.whitelist

    def get_minecraft_status(self, guild_id: int, minecraft_api_base: str) -> dict:
        _method = inspect.stack()[0][3]
        result = self.call_minecraft_status_api(minecraft_api_base=minecraft_api_base)
        if result.status_code != 200:
            raise Exception(f"Failed to get minecraft status ({result.status_code} - {result.text})")

        data = result.json()

        return data

    def is_user_whitelisted(self, guild_id: int, user_id: int) :
        # check if user is in the whitelist
        minecraft_user = self.minecraft_db.get_minecraft_user(guild_id=guild_id, user_id=user_id)
        if not minecraft_user:
            return False

        # check if user is whitelisted
        if not minecraft_user.whitelist:
            return False

        return True

    def set_user_whitelist_status(self, guild_id: int, user_id: int, username: str, uuid: str, status: bool):
        # set the whitelist status for a user
        minecraft_user = self.minecraft_db.get_minecraft_user(guild_id=guild_id, user_id=user_id)
        if not minecraft_user:
            return False

        self.minecraft_db.whitelist_minecraft_user(
            guildId=guild_id,
            userId=user_id,
            username=username,
            uuid=uuid,
            whitelist=status,
        )
        return True

    def call_minecraft_status_api(self, minecraft_api_base: str) -> requests.Response:
        """Get the current Minecraft server status.

        Returns:
            Response object from the API call
        """
        status_url = f"{minecraft_api_base}/tacobot/minecraft/status"
        return requests.get(status_url)
