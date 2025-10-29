# this is a cog that will allow admins to move messages to another channel
# this doesn't actually move the message. The bot will delete the original message
# and send the message to the new channel with the same content as the original.
# it will identify the original author in the new embeded message that is sent by the bot.

import inspect
import os
import traceback

import discord
from discord.ext import commands

from bot.lib import discordhelper, permissions
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.tacobot import TacoBot


class MoveMessageCog(TacobotCog):
    def __init__(self, bot: TacoBot):
        super().__init__(bot, "move_message")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.permissions = permissions.Permissions(bot)
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:
            # ignore if not in a guild
            if guild_id is None or guild_id == 0:
                return
            if payload.event_type != 'REACTION_ADD':
                return

            if str(payload.emoji) != '⏭️':
                return

            channel = await self.discord_helper.get_or_fetch_channel(payload.channel_id)
            if channel is None:
                return
            message = await channel.fetch_message(payload.message_id)
            if message is None:
                return
            user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if user is None or user.bot or user.system:
                return

            react_member = await self.discord_helper.get_or_fetch_member(guild_id, user.id)
            if self.permissions.has_permission(react_member, discord.Permissions(manage_messages=True)):
                # self.log.debug(guild_id, f"move_message.{_method}", f"{user.name} reacted to message {message.id} with {str(payload.emoji)}")
                if str(payload.emoji) == '⏭️':
                    ctx = self.discord_helper.create_context(
                        bot=self.bot, message=message, channel=channel, author=user, guild=message.guild
                    )

                    async def callback(target_channel):
                        await self.discord_helper.move_message(
                            message,
                            targetChannel=target_channel,
                            author=message.author,
                            who=ctx.author,
                            reason="Moved by admin",
                        )
                        await message.delete()

                    await self.discord_helper.ask_channel(
                        ctx=ctx,
                        title=self.settings.get_string(guild_id, "move_choose_channel_title"),
                        message=self.settings.get_string(guild_id, "move_choose_channel_message"),
                        timeout=60,
                        callback=callback,
                    )

                    self.tracking_db.track_command_usage(
                        guildId=guild_id,
                        channelId=ctx.channel.id if ctx.channel else None,
                        userId=ctx.author.id,
                        command="move-message",
                        subcommand=None,
                        args=[
                            {"type": "reaction"},
                            {
                                "payload": {
                                    "message_id": str(payload.message_id),
                                    "channel_id": str(payload.channel_id),
                                    "guild_id": str(payload.guild_id),
                                    "user_id": str(payload.user_id),
                                    "emoji": payload.emoji.name,
                                    "event_type": payload.event_type,
                                    # "burst": payload.burst,
                                }
                            },
                        ],
                    )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def move(self, ctx, messageId: int) -> None:
        _method = inspect.stack()[0][3]
        if ctx.invoked_subcommand is not None:
            return

        try:
            _method = inspect.stack()[0][3]
            if ctx.guild is None:
                return
            await ctx.message.delete()
            guild_id = ctx.guild.id
            # self.log.debug(guild_id, f"move_message.{_method}", f"{ctx.author.name} called move message {messageId}")
            channel = ctx.channel

            message = await ctx.channel.fetch_message(messageId)
            if message is None:
                await self.messaging.send_embed(
                    channel=channel,
                    title="Move Message",
                    message=self.settings.get_string(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        who=ctx.author.mention,
                        message_id=messageId,
                    ),
                    color=0xFF0000,
                    delete_after=20,
                )
                return
            ctx = self.discord_helper.create_context(
                bot=self.bot, message=message, channel=channel, author=message.author, guild=ctx.guild
            )
            target_channel = await self.discord_helper.ask_channel(
                ctx=ctx,
                title=self.settings.get_string(guild_id, "move_choose_channel_title"),
                message=self.settings.get_string(guild_id, "move_choose_channel_message"),
                timeout=60,
            )
            if target_channel is None:
                return

            await self.discord_helper.move_message(
                message=message,
                targetChannel=target_channel,
                author=message.author,
                who=ctx.author,
                reason="Moved by admin",
            )
            await message.delete()

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="move-message",
                subcommand="move",
                args=[{"type": "command"}, {"message_id": messageId}],
            )
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return


async def setup(bot):
    await bot.add_cog(MoveMessageCog(bot))
