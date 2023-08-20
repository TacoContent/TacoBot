import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import datetime

from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import tacotypes
from .lib.permissions import Permissions
from .lib.messaging import Messaging

import inspect


class TechThursdays(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.permissions = Permissions(bot)
        self.SETTINGS_SECTION = "techthurs"
        self.SELF_DESTRUCT_TIMEOUT = 30
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.group(name="techthurs", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def techthurs(self, ctx) -> None:
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
                    self.settings.get_string(guild_id, "techthurs_ask_title"),
                    self.settings.get_string(guild_id, "techthurs_ask_message"),
                    timeout=60 * 5,
                )
            except discord.Forbidden:
                _ctx = ctx
                twa = await self.discord_helper.ask_for_image_or_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "techthurs_ask_title"),
                    self.settings.get_string(guild_id, "techthurs_ask_message"),
                    timeout=60 * 5,
                )

            # ask the user for the techthurs in DM
            if twa is None or twa.text.lower() == "cancel":
                return

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"techthurs is disabled for guild {guild_id}")
                return

            tacos_settings = self.get_tacos_settings(guild_id)

            amount = tacos_settings.get("techthurs_amount", 5)

            role_tag = None
            role = ctx.guild.get_role(int(cog_settings.get("tag_role", 0)))
            if role:
                role_tag = f"{role.mention}"

            message_content = None
            if twa.text is not None and twa.text != "":
                if role_tag is not None:
                    message_content = f"{role_tag}\n\n{twa.text}"
                else:
                    message_content = twa.text
            else:
                if role_tag is not None:
                    message_content = role_tag

            out_channel = ctx.guild.get_channel(int(cog_settings.get("output_channel_id", 0)))
            if not out_channel:
                self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}")

            # get role
            taco_word = self.settings.get_string(guild_id, "taco_singular")
            if amount != 1:
                taco_word = self.settings.get_string(guild_id, "taco_plural")
            out_message = self.settings.get_string(
                guild_id, "techthurs_out_message", taco_count=amount, taco_word=taco_word
            )
            techthurs_message = await self.messaging.send_embed(
                channel=out_channel,
                title=self.settings.get_string(guild_id, "techthurs_out_title"),
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

            # save the techthurs to the database
            self.db.save_techthurs(
                guildId=guild_id,
                message=twa.text,
                image=twa.attachments[0].url,
                author=ctx.author.id,
                channel_id=out_channel.id,
                message_id=techthurs_message.id,
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @techthurs.command(name="import")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def import_techthurs(self, ctx, message_id: int) -> None:
        """Import techthurs from an existing post"""
        _method = inspect.stack()[0][3]
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        try:
            await ctx.message.delete()

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", f"No techthurs settings found for guild {guild_id}")
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"techthurs is disabled for guild {guild_id}")
                return

            out_channel = ctx.guild.get_channel(int(cog_settings.get("output_channel_id", 0)))
            if not out_channel:
                self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}")

            # get the message from the id
            message = await out_channel.fetch_message(message_id)
            if not message:
                return

            self._import_techthurs(message)

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @techthurs.command(name="give")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def give(self, ctx, member: discord.Member) -> None:
        _method = inspect.stack()[0][3]
        try:
            await ctx.message.delete()

            await self.give_user_techthurs_tacos(ctx.guild.id, member.id, ctx.channel.id, None)

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def _on_raw_reaction_add_give(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id

        # check if the user that reacted is in the admin role
        if not await self.permissions.is_admin(payload.user_id, guild_id):
            self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"User {payload.user_id} is not an admin")
            return
        # in future, check if the user is in a defined role that can grant tacos (e.g. moderator)

        # get the message that was reacted to
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        message_author = message.author
        react_user = await self.discord_helper.get_or_fetch_user(payload.user_id)

        if not react_user or react_user.bot or react_user.system:
            return

        # check if this reaction is the first one of this type on the message
        reactions = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        if reactions and reactions.count > 1:
            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}",
            )
            return

        already_tracked = self.db.techthurs_user_message_tracked(guild_id, message_author.id, message.id)
        if not already_tracked:
            # log that we are giving tacos for this reaction
            self.log.info(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"User {payload.user_id} reacted with {payload.emoji.name} to message {payload.message_id}",
            )
            await self.give_user_techthurs_tacos(guild_id, message_author.id, payload.channel_id, payload.message_id)
        else:
            self.log.debug(
                guild_id, f"{self._module}.{self._class}.{_method}", f"Message {payload.message_id} has already been tracked for techthurs. Skipping."
            )

    async def _on_raw_reaction_add_import(self, payload) -> None:
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id

        # check if the user that reacted is in the admin role
        if not await self.permissions.is_admin(payload.user_id, guild_id):
            self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"User {payload.user_id} is not an admin")
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

        self._import_techthurs(message)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:

            if payload.event_type != "REACTION_ADD":
                return

            # check if the user that reacted is in the admin role
            if not await self.permissions.is_admin(payload.user_id, guild_id):
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"User {payload.user_id} is not an admin")
                return


            react_user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if not react_user or react_user.bot or react_user.system:
                return

            cog_settings = self.get_cog_settings(guild_id)

            reaction_emojis = cog_settings.get("reaction_emoji", ["💻"])
            reaction_import_emojis = cog_settings.get("import_emoji", ["🇮"])
            check_list = reaction_emojis + reaction_import_emojis
            if str(payload.emoji.name) not in check_list:
                return

            if str(payload.emoji.name) in reaction_emojis:
                await self._on_raw_reaction_add_give(payload)
                return


            # is today thursday?
            today = datetime.datetime.now()
            if today.weekday() != 3:  # 0 = Monday, 1=Tuesday, 2=Wednesday...
                return
            if str(payload.emoji.name) in reaction_import_emojis:
                await self._on_raw_reaction_add_import(payload)
                return

        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # await self.messaging.notify_of_error(ctx)

    def _import_techthurs(self, message: discord.Message) -> None:
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

        # get the text
        text = None
        if message_content is not None and message_content != "":
            text = message_content

        self.log.debug(
            guild_id,
            f"{self._module}.{self._class}.{_method}",
            f"Importing techthurs message {message_id} from channel {channel_id} in guild {guild_id} for user {message_author.id} with text {text} and image {image_url}",
        )
        self.db.save_techthurs(
            guildId=guild_id,
            message=text or "",
            image=image_url,
            author=message_author.id,
            channel_id=channel_id,
            message_id=message_id,
        )

    async def give_user_techthurs_tacos(self, guild_id, user_id, channel_id, message_id) -> None:
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
            self.db.track_techthurs_answer(guild_id, member.id, message_id)

            tacos_settings = self.get_tacos_settings(guild_id)
            amount = tacos_settings.get("tech_thursday_count", 5)

            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reason_msg = self.settings.get_string(guild_id, "techthurs_reason_default")

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
                guild_id, self.bot.user, member, reason_msg, tacotypes.TacoTypes.TECH_THURSDAY, taco_amount=amount
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No techthurs settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings


async def setup(bot):
    await bot.add_cog(TechThursdays(bot))
