import discord
import discordhealthcheck
import inspect
import os
import sys
import traceback
import typing

from discord.ext import commands
from bot.cogs.lib import settings, mongo, logger, loglevel  # pylint: disable=no-name-in-module


class TacoBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        super().__init__(command_prefix=self.get_prefix, intents=intents, case_insensitive=True)
        self.remove_command("help")
        # self.command_prefix=self.get_prefix
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        # self.tree = app_commands.CommandTree(self)
        print(f"APP VERSION: {self.settings.APP_VERSION}")
        self.db = mongo.MongoDatabase()
        self.initDB()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Logger initialized with level {log_level.name}")

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
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
                print(f"Failed to load extension {extension}.", file=sys.stderr)
                traceback.print_exc()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Setting up bot")
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
                settings = self.settings.get_settings(self.db, guild_id, "tacobot")
                if not settings:
                    raise Exception("No bot settings found")
                prefixes = settings["command_prefixes"]

            elif not message.guild:
                # get the prefix for the DM using 0 for the guild_id
                settings = self.settings.get_settings(self.db, 0, "tacobot")
                if not settings:
                    raise Exception("No bot settings found")
                prefixes = settings["command_prefixes"]
            # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
            # Do `return prefixes` if you don't want to allow mentions instead of prefix.
            return commands.when_mentioned_or(*prefixes)(self, message)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"Failed to get prefixes: {e}")
            return commands.when_mentioned_or(*prefixes)(self, message)
