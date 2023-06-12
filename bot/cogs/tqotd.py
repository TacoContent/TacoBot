import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import io
import glob
import typing
import aiohttp

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

class TacoQuestionOfTheDay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "tqotd"
        self.SELF_DESTRUCT_TIMEOUT = 30
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "tqotd.__init__", "Initialized")

    @commands.group(name="tqotd", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def tqotd(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        guild_id = 0
        try:
            await ctx.message.delete()
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id
            qotd = None

            try:
                _ctx = self.discord_helper.create_context(self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild)
                qotd = await self.discord_helper.ask_for_image_or_text(_ctx, ctx.author,
                    self.settings.get_string(guild_id, "tqotd_ask_title"),
                    self.settings.get_string(guild_id, "tqotd_ask_message"),
                    timeout=60 * 5)
            except discord.Forbidden:
                _ctx = ctx
                qotd = await self.discord_helper.ask_for_image_or_text(_ctx, ctx.author,
                    self.settings.get_string(guild_id, "tqotd_ask_title"),
                    self.settings.get_string(guild_id, "tqotd_ask_message"),
                    timeout=60 * 5)

            # ask the user for the TQOTD in DM
            if qotd is None or qotd.text.lower() == "cancel":
                return

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(guild_id, "tqotd.tqotd", f"No tqotd settings found for guild {guild_id}")
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, "tqotd.tqotd", f"tqotd is disabled for guild {guild_id}")
                return

            tacos_settings = self.get_tacos_settings(guild_id)
            if not tacos_settings:
                self.log.warn(guild_id, "tqotd.tqotd", f"No tacos settings found for guild {guild_id}")
                return

            amount = tacos_settings.get("tqotd_amount", 5)

            role_tag = ""
            role = ctx.guild.get_role(int(cog_settings.get("tag_role", 0)))
            if role:
                role_tag = f"{role.mention}"

            out_channel = ctx.guild.get_channel(int(cog_settings.get("output_channel_id", 0)))
            if not out_channel:
                self.log.warn(guild_id, "tqotd.tqotd", f"No output channel found for guild {guild_id}")

            # get role
            taco_word = self.settings.get_string(guild_id, "taco_singular")
            if amount != 1:
                taco_word = self.settings.get_string(guild_id, "taco_plural")
            out_message = self.settings.get_string(guild_id, "tqotd_out_message", question=qotd.text, taco_count=amount, taco_word=taco_word)
            if qotd.attachments and len(qotd.attachments) > 0:
                urls = ""
                for attachment in qotd.attachments:
                    urls += f"{attachment.url}\n"
                save_message = f"{out_message}\n\n{urls}"
            else:
                save_message = out_message
            files = []
            if qotd.attachments and len(qotd.attachments) > 0:
                for attachment in qotd.attachments:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status != 200:
                                self.log.warn(guild_id, "tqotd.tqotd", f"Unable to download attachment {attachment.url}")
                                continue
                            data = io.BytesIO(await resp.read())
                            files.append(discord.File(data, filename=attachment.filename))

            await self.discord_helper.sendEmbed(
                channel=out_channel,
                title=self.settings.get_string(guild_id, "tqotd_out_title"),
                 message=out_message,
                 content=role_tag,
                 files=files,
                 color=0x00ff00)

            # save the TQOTD
            self.db.save_tqotd(guild_id, qotd.text, ctx.author.id)

        except Exception as e:
            self.log.error(guild_id, "tqotd.tqotd", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @tqotd.command(name="give")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def give(self, ctx, member: discord.Member):
        try:
            await ctx.message.delete()

            await self.give_user_tqotd_tacos(ctx.guild.id, member.id, ctx.channel.id, None)

        except Exception as e:
            self.log.error(ctx.guild.id, "tqotd.give", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:
            if payload.event_type != 'REACTION_ADD':
                return

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                # raise exception if there are no tacos settings
                self.log.error(guild_id, "tqotd.on_raw_reaction_add", f"No cog settings found for guild {guild_id}")
                return

            reaction_emojis = cog_settings.get("tqotd_reaction_emoji", ["🇹"])
            # check if the reaction is in the list of ones we are looking for
            if str(payload.emoji.name) not in reaction_emojis:
                # self.log.debug(guild_id, "tqotd.on_raw_reaction_add", f"Reaction {payload.emoji.name} is not in the list of ones we are looking for {reaction_emojis}")
                return

            # check if the user that reacted is in the admin role
            if not await self.discord_helper.is_admin(guild_id, payload.user_id):
                self.log.debug(guild_id, f"tqotd.{_method}", f"User {payload.user_id} is not an admin")
                return
            # in the future, check if the user is in a defined role that can grant tacos (e.g. moderator)

            # get the message that was reacted to
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            message_author = message.author
            react_user = await self.discord_helper.get_or_fetch_user(payload.user_id)

            # check if this reaction is the first one of this type on the message
            reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name)
            if reaction.count > 1:
                # self.log.debug(guild_id, f"tqotd.{_method}", f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}")
                return

            already_tracked = self.db.tqotd_user_message_tracked(guild_id, message_author.id, message.id)

            if not already_tracked:
                # log that we are giving tacos for this reaction
                self.log.info(guild_id, f"tqotd.{_method}", f"User {payload.user_id} reacted with {payload.emoji.name} to message {payload.message_id}")
                await self.give_user_tqotd_tacos(guild_id, message_author.id, payload.channel_id, payload.message_id)
            else:
                self.log.debug(guild_id, f"tqotd.{_method}", f"Message {payload.message_id} has already been tracked for TQOTD. Skipping.")

        except Exception as ex:
            self.log.error(guild_id, f"tqotd.{_method}", str(ex), traceback.format_exc())

    async def give_user_tqotd_tacos(self, guild_id, user_id, channel_id, message_id):
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
                self.log.warn(guild_id, "tqotd.give_user_tqotd_tacos", f"No output channel found for guild {guild_id}")
                return
            message = None
            # get message
            if message_id and channel:
                message = await channel.fetch_message(message_id)

            # get bot
            bot = self.bot
            ctx = self.discord_helper.create_context(bot=bot, guild=guild, author=member, channel=channel, message=message)
            # track that the user answered the question.
            self.db.track_tqotd_answer(guild_id, member.id, message_id)

            tacos_settings = self.get_tacos_settings(guild_id)
            if not tacos_settings:
                self.log.warn(guild_id, "tqotd.give_user_tqotd_tacos", f"No tacos settings found for guild {guild_id}")
                return

            amount = tacos_settings.get("tqotd_count", 5)

            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reason_msg = self.settings.get_string(guild_id, "tqotd_reason_default")

            await self.discord_helper.sendEmbed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "taco_give_title"),
                # 	"taco_gift_success": "{{user}}, You gave {touser} {amount} {taco_word} 🌮.\n\n{{reason}}",
                message=self.settings.get_string(guild_id, "taco_gift_success", user=self.bot.user, touser=member.mention, amount=amount, taco_word=tacos_word, reason=reason_msg),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT)

            await self.discord_helper.taco_give_user(guild_id, self.bot.user, member, reason_msg, tacotypes.TacoTypes.TQOTD, taco_amount=amount )


        except Exception as e:
            self.log.error(guild_id, "tqotd.give_user_tqotd_tacos", str(e), traceback.format_exc())
            raise e

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No tqotd settings found for guild {guildId}")
        return cog_settings
    def get_tacos_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings
async def setup(bot):
    await bot.add_cog(TacoQuestionOfTheDay(bot))
