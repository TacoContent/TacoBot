import inspect
import os

import discord
from bot import tacobot  # pylint: disable=relative-beyond-top-level
from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from discord.ext import commands


class LookingForGamersCog(TacobotCog):
    def __init__(self, bot: tacobot.TacoBot) -> None:
        super().__init__(bot, "lfg")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discordhelper.DiscordHelper(bot)

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    # @commands.group(name="lfg", aliases=["looking-for-gamers"], invoke_without_command=True)
    # @commands.guild_only()
    # @app_commands.guild_only()
    # @app_commands.command(name="lfg", description="Looking for gamers")
    async def looking_for_gamers_app(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("lfg")

    @commands.group(name="lfg", aliases=["looking-for-gamers"], invoke_without_command=True)
    @commands.guild_only()
    async def looking_for_gamers_cmd(self, ctx) -> None:
        await self._looking_for_gamers(ctx)

    async def _looking_for_gamers(self, ctx) -> None:
        await ctx.channel.send("lfg")


async def setup(bot) -> None:
    await bot.add_cog(LookingForGamersCog(bot))
