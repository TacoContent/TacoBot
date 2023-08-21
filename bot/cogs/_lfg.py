import discord
from discord.ext import commands
from discord import app_commands
import inspect
import os
from .. import tacobot
from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import mongo


class LookingForGamers(commands.Cog):
    def __init__(self, bot: tacobot.TacoBot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "lfg"
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    # @commands.group(name="lfg", aliases=["looking-for-gamers"], invoke_without_command=True)
    # @commands.guild_only()
    # @app_commands.guild_only()
    # @app_commands.command(name="lfg", description="Looking for gamers")
    async def looking_for_gamers_app(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("lfg")

    @commands.group(
        name="lfg", aliases=["looking-for-gamers"], invoke_without_command=True
    )
    @commands.guild_only()
    async def looking_for_gamers_cmd(self, ctx) -> None:
        await self._looking_for_gamers(ctx)

    async def _looking_for_gamers(self, ctx) -> None:
        await ctx.channel.send("lfg")


async def setup(bot) -> None:
    await bot.add_cog(LookingForGamers(bot))
