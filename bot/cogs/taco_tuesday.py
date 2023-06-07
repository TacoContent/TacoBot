import discord
from discord.ext import commands
import asyncio
import json
import traceback
import datetime
import sys
import os
import glob
import typing

from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands import has_permissions, CheckFailure, Context

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider
from .lib import tacotypes

import inspect


class TacoTuesday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "tacotuesday"
        self.SELF_DESTRUCT_TIMEOUT = 30
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "taco_tuesday.__init__", "Initialized")

    @commands.group()
    async def tuesday(self, ctx):
        pass

    @tuesday.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def give(self, ctx, member: discord.Member):
        try:
            await ctx.message.delete()

            await self.give_user_tacotuesday_tacos(ctx.guild.id, member.id, ctx.channel.id)

        except Exception as e:
            self.log.error(ctx.guild.id, "taco_tuesday.give", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)


    # async def give(self, ctx: Context, member: discord.Member):
    #     guild_id = ctx.guild.id
    #     try:

    #         await ctx.message.delete()
    #         taco_settings = self.get_tacos_settings(guildId = guild_id)
    #         if not taco_settings:
    #             # raise exception if there are no tacos settings
    #             self.log.error(guild_id, "tacos.on_raw_reaction_add", f"No tacos settings found for guild {guild_id}")
    #             return

    #         amount = taco_settings.get("taco_tuesday_count", 250)
    #         reason = taco_settings.get("taco_tuesday_reason", "Taco Tuesday Tacos")

    #         tacos_word = self.settings.get_string(guild_id, "taco_singular")
    #         if amount > 1:
    #             tacos_word = self.settings.get_string(guild_id, "taco_plural")

    #         reason_msg = self.settings.get_string(guild_id, "taco_reason_default")
    #         if reason:
    #             reason_msg = f"{reason}"

    #         await self.discord_helper.sendEmbed(ctx.channel,
    #             self.settings.get_string(guild_id, "taco_give_title"),
    #             # 	"taco_gift_success": "{{user}}, You gave {touser} {amount} {taco_word} 🌮.\n\n{{reason}}",
    #             self.settings.get_string(guild_id, "taco_gift_success", user=self.bot.user, touser=member.mention, amount=amount, taco_word=tacos_word, reason=reason_msg),
    #             footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
    #             delete_after=self.SELF_DESTRUCT_TIMEOUT)

    #         await self.discord_helper.taco_give_user(
    #             guildId=guild_id,
    #             fromUser=self.bot.user,
    #             toUser=member,
    #             reason=reason_msg,
    #             give_type=tacotypes.TacoTypes.CUSTOM,
    #             taco_amount=amount
    #         )

    #     except Exception as e:
    #         self.log.error(ctx.guild.id, "taco_tuesday.give", str(e), traceback.format_exc())
    #         await self.discord_helper.notify_of_error(ctx)

    async def _on_raw_reaction_add_import(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id


        # check if the user that reacted is in the admin role
        if not await self.discord_helper.is_admin(guild_id, payload.user_id):
            self.log.debug(guild_id, _method, f"User {payload.user_id} is not an admin")
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        if reaction.count > 1:
            self.log.debug(guild_id, _method, f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}")
            return

        self._import_taco_tuesday(message)

    async def _on_raw_reaction_add_archive(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id

        # check if the user that reacted is in the admin role
        if not await self.discord_helper.is_admin(guild_id, payload.user_id):
            self.log.debug(guild_id, _method, f"User {payload.user_id} is not an admin")
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        cog_settings = self.get_cog_settings(guild_id)
        if not cog_settings:
            # raise exception if there are no cog settings
            self.log.error(guild_id, "tacotuesday.on_raw_reaction_add", f"No tacotuesday cog settings found for guild {guild_id}")
            return

        # check if message has the import emoji
        was_imported = False
        for m in message.reactions:
            if str(m.emoji) in cog_settings.get("import_emoji", []):
                was_imported = True
                break
        if not was_imported:
            self.log.debug(guild_id, _method, f"Message {payload.message_id} was not imported. No need to archive.")
            return

        reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        if reaction.count > 1:
            self.log.debug(guild_id, _method, f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}")
            return

        await self._archive_taco_tuesday(message, cog_settings)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:
            if payload.event_type != 'REACTION_ADD':
                return


            ###
            # archive_enabled: true,
            # archive_emoji: [
            #     '🔒'
            # ],
            # archive_channel_id: '948689068961706034',
            ###

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                # raise exception if there are no cog settings
                self.log.error(guild_id, "tacotuesday.on_raw_reaction_add", f"No tacotuesday cog settings found for guild {guild_id}")
                return

            if not cog_settings.get("enable", False):
                return

            # check if reaction is to archive the message
            reaction_archive_emojis = cog_settings.get("tacotuesday_reaction_archive_emoji", ["🔒"])
            if str(payload.emoji.name) in reaction_archive_emojis:
                if cog_settings.get("tacotuesday_archive_enabled", False):
                    await self._on_raw_reaction_add_archive(payload)

            today = datetime.datetime.now()
            if today.weekday() != 1: # 1 = Tuesday
                return

            reaction_import_emojis = cog_settings.get("tacotuesday_reaction_import_emoji", ["🇮"])
            if str(payload.emoji.name) in reaction_import_emojis:
                await self._on_raw_reaction_add_import(payload)
                return

        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            # await self.discord_helper.notify_of_error(ctx)

    async def _archive_taco_tuesday(self, message: discord.Message, cog_settings: dict = None):
        _method = inspect.stack()[0][3]
        guild_id = message.guild.id
        try:

            archive_channel_id = cog_settings.get("archive_channel_id", None)
            if not archive_channel_id:
                self.log.error(guild_id, "tacotuesday._archive_taco_tuesday", f"No archive_channel_id found for guild {guild_id}")
                return

            archive_channel = self.bot.get_channel(archive_channel_id)
            if not archive_channel:
                self.log.error(guild_id, "tacotuesday._archive_taco_tuesday", f"Could not find archive channel {archive_channel_id} for guild {guild_id}")
                return


            await self.discord_helper.move_message(
                message=message,
                targetChannel=archive_channel,
                who=self.bot.user,
                reason="TACO Tuesday archive")

            await self.discord_helper.sendEmbed(
                message.channel, title="TACO Tuesday",
                message=f"Message archived to {archive_channel.mention}",
                color=discord.Color.green().value,
                delete_after=10)

        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            # await self.discord_helper.notify_of_error(ctx)

    def _import_taco_tuesday(self, message: discord.Message):
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

        self.log.debug(guild_id, "taco_tuesday._import_taco_tuesday", f"Importing TACO Tuesday message {message_id} from channel {channel_id} in guild {guild_id} for user {message_author.id} with text {text} and image {image_url}")
        self.db.save_taco_tuesday (
            guildId=guild_id,
            message=text or "",
            image=image_url or "",
            author=message_author.id,
            channel_id=channel_id,
            message_id=message_id,
        )


    async def give_user_tacotuesday_tacos(self, guild_id, user_id, channel_id):
        ctx = None
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
                self.log.warn(guild_id, "tacotuesday.give_user_tacotuesday_tacos", f"No output channel found for guild {guild_id}")
                return
            message = None

            # get bot
            bot = self.bot
            ctx = self.discord_helper.create_context(bot=bot, guild=guild, author=member, channel=channel, message=message)

            # track that the user answered the question.
            self.db.track_taco_tuesday(guild_id, member.id)

            tacos_settings = self.get_tacos_settings(guild_id)
            if not tacos_settings:
                self.log.warn(guild_id, "tacotuesday.give_user_tacotuesday_tacos", f"No tacos settings found for guild {guild_id}")
                return

            amount = tacos_settings.get("taco_tuesday_count", 250)

            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reason_msg = self.settings.get_string(guild_id, "taco_tuesday_reason")

            await self.discord_helper.sendEmbed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "taco_give_title"),
                # 	"taco_gift_success": "{{user}}, You gave {touser} {amount} {taco_word} 🌮.\n\n{{reason}}",
                message=self.settings.get_string(guild_id, "taco_gift_success", user=self.bot.user, touser=member.mention, amount=amount, taco_word=tacos_word, reason=reason_msg),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT)

            await self.discord_helper.taco_give_user(guild_id, self.bot.user, member, reason_msg, tacotypes.TacoTypes.CUSTOM, taco_amount=amount )


        except Exception as e:
            self.log.error(guild_id, "tacotuesday.give_user_tacotuesday_tacos", str(e), traceback.format_exc())
            if ctx:
                await self.discord_helper.notify_of_error(ctx)

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No wdyctw settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings

async def setup(bot):
    await bot.add_cog(TacoTuesday(bot))
