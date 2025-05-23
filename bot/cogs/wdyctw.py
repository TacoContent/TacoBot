import datetime
import inspect
import os
import traceback

import discord
from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums import tacotypes
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.mongodb.wdyctw import WDYCTWDatabase
from bot.lib.permissions import Permissions
from bot.tacobot import TacoBot
from discord.ext import commands
from discord.ext.commands import Context


class WhatDoYouCallThisWednesdayCog(TacobotCog):
    def __init__(self, bot: TacoBot) -> None:
        super().__init__(bot, "wdyctw")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.permissions = Permissions(bot)
        self.SELF_DESTRUCT_TIMEOUT = 30

        self.wdyctw_db = WDYCTWDatabase()
        self.tracking_db = TrackingDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.group(name="wdyctw", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def wdyctw(self, ctx: Context) -> None:
        _method = inspect.stack()[0][3]
        if ctx.invoked_subcommand is not None:
            return
        guild_id = 0
        try:
            await ctx.message.delete()
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            # needs to accept an image along with the text
            try:
                _ctx = self.discord_helper.create_context(
                    self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild
                )
                twa = await self.discord_helper.ask_for_image_or_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "wdyctw_ask_title"),
                    self.settings.get_string(guild_id, "wdyctw_ask_message"),
                    timeout=60 * 5,
                )
            except discord.Forbidden:
                _ctx = ctx
                twa = await self.discord_helper.ask_for_image_or_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "wdyctw_ask_title"),
                    self.settings.get_string(guild_id, "wdyctw_ask_message"),
                    timeout=60 * 5,
                )

            # ask the user for the WDYCTW in DM
            if twa is None or twa.text.lower() == "cancel" or twa.attachments is None or len(twa.attachments) == 0:
                return

            cog_settings = self.get_cog_settings(guild_id)
            tacos_settings = self.get_tacos_settings(guild_id)

            amount = tacos_settings.get("wdyctw_amount", 5)

            role_tag = ""
            role = ctx.guild.get_role(int(cog_settings.get("tag_role", 0)))
            if role:
                role_tag = f"{role.mention}"

            message_content = ""
            if twa.text is not None and twa.text != "":
                if role_tag is not None:
                    message_content = f"{role_tag}\n\n{twa.text}"
                else:
                    message_content = twa.text
            else:
                if role_tag is not None:
                    message_content = role_tag

            out_channel = ctx.guild.get_channel(int(cog_settings.get("output_channel_id", 0)))
            if out_channel is None:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}"
                )
                return

            # get role
            taco_word = self.settings.get_string(guild_id, "taco_singular")
            if amount != 1:
                taco_word = self.settings.get_string(guild_id, "taco_plural")
            out_message = self.settings.get_string(
                guild_id, "wdyctw_out_message", taco_count=amount, taco_word=taco_word
            )
            wdyctw_message = await self.messaging.send_embed(
                channel=out_channel,
                title=self.settings.get_string(guild_id, "wdyctw_out_title"),
                message=out_message,
                content=message_content,
                color=0x00FF00,
                image=twa.attachments[0].url,
                thumbnail=None,
                footer=None,
                author=None,
                fields=None,
                delete_after=None,
            )

            # save the WDYCTW to the database
            self.wdyctw_db.save_wdyctw(
                guildId=guild_id,
                message=twa.text,
                image=twa.attachments[0].url,
                author=ctx.author.id,
                channel_id=out_channel.id,
                message_id=wdyctw_message.id,
            )
            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel.id else None,
                userId=ctx.author.id,
                command="wdyctw",
                subcommand=None,
                args=[{"type": "command"}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @wdyctw.command(name="import")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def import_wdyctw(self, ctx, message_id: int) -> None:
        """Import WDYCTW from an existing post"""
        _method = inspect.stack()[0][3]
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        try:
            await ctx.message.delete()

            cog_settings = self.get_cog_settings(guild_id)

            out_channel = ctx.guild.get_channel(int(cog_settings.get("output_channel_id", 0)))
            if not out_channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}"
                )

            # get the message from the id
            message = await out_channel.fetch_message(message_id)
            if not message:
                return

            self._import_wdyctw(message)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel.id else None,
                userId=ctx.author.id,
                command="wdyctw",
                subcommand="import",
                args=[{"type": "command"}, {"message_id": str(message.id)}],
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @wdyctw.command(name="give")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def give(self, ctx, member: discord.Member) -> None:
        """Give a user tacos for their WDYCTW"""
        _method = inspect.stack()[0][3]
        try:
            await ctx.message.delete()

            await self.give_user_wdyctw_tacos(ctx.guild.id, member.id, ctx.channel.id, None)

            self.tracking_db.track_command_usage(
                guildId=ctx.guild.id,
                channelId=ctx.channel.id if ctx.channel.id else None,
                userId=ctx.author.id,
                command="wdyctw",
                subcommand="give",
                args=[{"type": "command"}, {"member_id": str(member.id)}],
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def _on_raw_reaction_add_give(self, payload) -> None:
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id

        # check if the user that reacted is in the admin role
        if not await self.permissions.is_admin(payload.user_id, guild_id):
            self.log.debug(
                guild_id, f"{self._module}.{self._class}.{_method}", f"User {payload.user_id} is not an admin"
            )
            return
        # in future, check if the user is in a defined role that can grant tacos (e.g. moderator)

        # get the message that was reacted to
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        message_author = message.author
        # react_user = await self.discord_helper.get_or_fetch_user(payload.user_id)

        # check if this reaction is the first one of this type on the message
        reactions = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        if reactions and reactions.count > 1:
            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}",
            )
            return

        already_tracked = self.wdyctw_db.wdyctw_user_message_tracked(guild_id, message_author.id, message.id)
        if not already_tracked:
            # log that we are giving tacos for this reaction
            self.log.info(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"User {payload.user_id} reacted with {payload.emoji.name} to message {payload.message_id}",
            )
            await self.give_user_wdyctw_tacos(guild_id, message_author.id, payload.channel_id, payload.message_id)
            self.tracking_db.track_command_usage(
                guildId=payload.guild_id,
                channelId=payload.channel_id if payload.channel_id else None,
                userId=payload.user_id,
                command="wdyctw",
                subcommand="give",
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
        else:
            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Message {payload.message_id} has already been tracked for WDYCTW. Skipping.",
            )

    async def _on_raw_reaction_add_import(self, payload) -> None:
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id

        # check if the user that reacted is in the admin role
        if not await self.permissions.is_admin(payload.user_id, guild_id):
            self.log.debug(
                guild_id, f"{self._module}.{self._class}.{_method}", f"User {payload.user_id} is not an admin"
            )
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        # check if this reaction is the first one of this type on the message
        reactions = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        if reactions and reactions.count > 1:
            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}",
            )
            return

        self._import_wdyctw(message)

        self.tracking_db.track_command_usage(
            guildId=payload.guild_id,
            channelId=payload.channel_id if payload.channel_id else None,
            userId=payload.user_id,
            command="wdyctw",
            subcommand="import",
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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload) -> None:
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:
            if payload.event_type != 'REACTION_ADD':
                return

            # check if the user that reacted is in the admin role
            if not await self.permissions.is_admin(payload.user_id, guild_id):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"User {payload.user_id} is not an admin"
                )
                return

            react_user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if not react_user or react_user.bot or react_user.system:
                return

            cog_settings = self.get_cog_settings(guild_id)

            # check if the reaction is one of the ones we care about
            reaction_emojis = cog_settings.get("reaction_emoji", ["🇼"])
            reaction_import_emojis = cog_settings.get("import_emoji", ["🇮"])

            check_list = reaction_emojis + reaction_import_emojis
            if str(payload.emoji.name) not in check_list:
                return

            if str(payload.emoji.name) in reaction_emojis:
                await self._on_raw_reaction_add_give(payload)
                return

            # check if it's Wednesday
            today = datetime.datetime.now()
            if today.weekday() != 2:  # 2 = Wednesday
                return
            if str(payload.emoji.name) in reaction_import_emojis:
                await self._on_raw_reaction_add_import(payload)
                return

        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # await self.messaging.notify_of_error(ctx)

    def _import_wdyctw(self, message: discord.Message) -> None:
        _method = inspect.stack()[0][3]
        guild_id = message.guild.id
        channel_id = message.channel.id
        message_id = message.id
        message_author = message.author
        message_content = message.content

        # get the image
        image_url = None
        if message.attachments is not None and len(message.attachments) > 0:
            image_url = message.attachments[0].url
        else:
            raise Exception("No image found in message")

        # get the text
        text = None
        if message_content is not None and message_content != "":
            text = message_content

        self.log.debug(
            guild_id,
            f"{self._module}.{self._class}.{_method}",
            f"Importing WDYCTW message {message_id} from channel {channel_id} in guild {guild_id} for user {message_author.id} with text {text} and image {image_url}",
        )
        self.wdyctw_db.save_wdyctw(
            guildId=guild_id,
            message=text or "",
            image=image_url,
            author=message_author.id,
            channel_id=channel_id,
            message_id=message_id,
        )

    async def give_user_wdyctw_tacos(self, guild_id, user_id, channel_id, message_id) -> None:
        _method = inspect.stack()[0][3]
        try:
            # create context
            # self, bot=None, author=None, guild=None, channel=None, message=None, invoked_subcommand=None, **kwargs
            # get guild from id
            guild = self.bot.get_guild(guild_id)
            # fetch member from id
            member = guild.get_member(user_id)
            # get channel
            channel = None
            if channel_id:
                channel = self.bot.get_channel(channel_id)
            else:
                channel = guild.system_channel
            if not channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}"
                )
                return
            message = None
            # get message
            if message_id and channel:
                message = await channel.fetch_message(message_id)

            # get bot
            bot = self.bot
            ctx = self.discord_helper.create_context(
                bot=bot, guild=guild, author=member, channel=channel, message=message
            )

            # track that the user answered the question.
            self.wdyctw_db.track_wdyctw_answer(guild_id, member.id, message_id)

            tacos_settings = self.get_tacos_settings(guild_id)

            amount = tacos_settings.get("wdyctw_count", 5)

            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reason_msg = self.settings.get_string(guild_id, "wdyctw_reason_default")

            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "taco_give_title"),
                # 	"taco_gift_success": "{{user}}, You gave {touser} {amount} {taco_word} 🌮.\n\n{{reason}}",
                message=self.settings.get_string(
                    guild_id,
                    "taco_gift_success",
                    user=self.bot.user,
                    touser=member.mention,
                    amount=amount,
                    taco_word=tacos_word,
                    reason=reason_msg,
                ),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT,
            )

            await self.discord_helper.taco_give_user(
                guild_id, self.bot.user, member, reason_msg, tacotypes.TacoTypes.WDYCTW, taco_amount=amount
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)


async def setup(bot):
    await bot.add_cog(WhatDoYouCallThisWednesdayCog(bot))
