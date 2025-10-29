import inspect
import os
import traceback
import typing

import discord
import discordhealthcheck
from discord.ext import commands

from bot.lib import logger, settings
from bot.lib.enums import loglevel
from bot.lib.mongodb.guilds import GuildsDatabase


class TacoBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        self.guilds_db = GuildsDatabase()
        super().__init__(command_prefix=self.get_prefix, intents=intents, case_insensitive=True)
        self.remove_command("help")

        self.initDB()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"APP VERSION: {self.settings.APP_VERSION}")
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Logger initialized with level {log_level.name}")

    async def setup_hook(self) -> None:
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Setup hook called")
        # cogs that dont start with an underscore are loaded
        cogs = [
            f"bot.cogs.{os.path.splitext(f)[0]}"
            for f in os.listdir("bot/cogs")
            if f.endswith(".py") and not f.startswith("_")
        ]

        for extension in cogs:
            try:
                await self.load_extension(extension)
            except Exception as e:
                self.log.error(
                    0,
                    f"{self._module}.{self._class}.{_method}",
                    f"Failed to load extension {extension}: {e}",
                    traceback.format_exc(),
                )

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Setting up bot")
        guilds = [int(g) for g in self.guilds_db.get_guild_ids()]
        # guilds = [g for g in self.guilds]
        for gid in guilds:
            try:
                # gid = guild.id
                if self.settings.sync_app_commands:
                    guild = discord.Object(id=gid)
                    self.tree.clear_commands(guild=guild)
                    self.log.debug(
                        gid, f"{self._module}.{self._class}.{_method}", f"Clearing app commands for guild {gid}"
                    )
                    self.tree.copy_global_to(guild=guild)

                    await self.tree.sync(guild=guild)
                    self.log.debug(
                        gid, f"{self._module}.{self._class}.{_method}", f"Synced app commands for guild {gid}"
                    )
                else:
                    self.log.info(
                        gid,
                        f"{self._module}.{self._class}.{_method}",
                        f"Skipping sync app commands for guild {gid} due to SYNC_APP_COMMANDS being false",
                    )
            except discord.errors.Forbidden as fe:
                self.log.debug(
                    gid, f"{self._module}.{self._class}.{_method}", f"Failed to sync app commands for guild {gid}: {fe}"
                )

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Starting Healthcheck Server")
        self.healthcheck_server = await discordhealthcheck.start(self)

    def initDB(self) -> None:
        pass

    async def get_prefix(self, message) -> typing.List[str]:
        _method: str = inspect.stack()[0][3]
        # default prefixes
        # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
        prefixes: typing.List[str] = [".taco ", "?taco ", "!taco "]
        try:
            # get the prefix for the guild.
            if message.guild:
                guild_id = message.guild.id
                # get settings from db
                settings = self.settings.get_settings(guild_id, "tacobot")
                if not settings:
                    raise Exception("No bot settings found")
                prefixes = settings["command_prefixes"]

            elif not message.guild:
                # get the prefix for the DM using 0 for the guild_id
                settings = self.settings.get_settings(0, "tacobot")
                if not settings:
                    raise Exception("No bot settings found")
                prefixes = settings["command_prefixes"]
            # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
            # Do `return prefixes` if you don't want to allow mentions instead of prefix.
            # return commands.when_mentioned_or(*prefixes)(self, message)
            return prefixes
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"Failed to get prefixes: {e}")
            return commands.when_mentioned_or(*prefixes)(self, message)
