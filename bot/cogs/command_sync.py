import inspect
import os
import typing

import discord
from discord.ext import commands
from discord.ext.commands import Context, Greedy

from bot import tacobot  # pylint: disable=no-name-in-module
from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.messaging import Messaging


class CommandSyncCog(TacobotCog):
    def __init__(self, bot: tacobot.TacoBot) -> None:
        super().__init__(bot, "command_sync")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.group("command", aliases=["c", "commands"], invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def app_command(self, ctx: Context) -> None:
        pass

    @app_command.command(name="sync", aliases=["s"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def sync(
        self, ctx: Context, guilds: Greedy[discord.Object], spec: typing.Optional[typing.Literal["~", "*", "^"]] = None
    ) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id if ctx.guild else 0
        try:
            await ctx.message.delete()
            if not guilds:
                if spec == "~":
                    synced = await self.bot.tree.sync(guild=ctx.guild)
                elif spec == "*":
                    if guild_id == 0:
                        await self.messaging.send_embed(
                            channel=ctx.channel,
                            title="Command Sync",
                            message="No guild id identified, cannot sync globally.",
                            delete_after=15,
                        )
                        return
                    self.bot.tree.copy_global_to(guild=discord.Object(guild_id))
                    synced = await self.bot.tree.sync(guild=ctx.guild)
                elif spec == "^":
                    self.bot.tree.clear_commands(guild=ctx.guild)
                    await self.bot.tree.sync(guild=ctx.guild)
                    synced = []
                else:
                    synced = await self.bot.tree.sync()

                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title="Command Sync",
                    message=f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}",
                    delete_after=15,
                )
                return

            ret = 0
            for guild in guilds:
                try:
                    await self.bot.tree.sync(guild=guild)
                except discord.HTTPException as e:
                    self.log.debug(
                        guild_id, f"{self._module}.{self._class}.{_method}", f"Failed to sync guild {guild.id}: {e}"
                    )
                    pass
                else:
                    ret += 1
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title="Command Sync",
                    message=f"Synced the tree to {ret}/{len(guilds)}",
                    delete_after=15,
                )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"Exception: {e}")
            await self.messaging.notify_of_error(ctx)


async def setup(bot):
    await bot.add_cog(CommandSyncCog(bot))
