import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing

from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands import has_permissions, CheckFailure

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

class Tacos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "tacos"
        self.SELF_DESTRUCT_TIMEOUT = 30
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "tacos.__init__", "Initialized")

    @commands.group()
    async def tacos(self, ctx):
        pass

    @tacos.command()
    @commands.guild_only()
    async def help(self, ctx):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
            await ctx.message.delete()
        await self.discord_helper.sendEmbed(ctx.channel,
            self.settings.get_string(guild_id, "help_title", bot_name=self.settings.name),
            self.settings.get_string(guild_id, "help_module_message", command="tacos"),
            footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
            color=0xff0000, delete_after=30)

    # create command called remove_all_tacos that asks for the user
    @tacos.command(aliases=['purge'])
    @commands.has_permissions(administrator=True)
    async def remove_all_tacos(self, ctx, user: discord.Member, *, reason: str = None):
        try:
            guild_id = ctx.guild.id
            await ctx.message.delete()
            self.db.remove_all_tacos(guild_id, user.id)
            reason_msg = reason if reason else "No reason given."
            await self.discord_helper.sendEmbed(ctx.channel, "Removed All Tacos", f"{user.mention} has lost all their tacos.", delete_after=self.SELF_DESTRUCT_TIMEOUT)
            await self.discord_helper.taco_purge_log(ctx.guild.id, user, ctx.author, reason_msg)

        except Exception as e:
            await self.discord_helper.notify_of_error(ctx, e)
            await ctx.message.delete()

    @tacos.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def give(self, ctx, member: discord.Member, amount: int, *, reason: str = None):
        try:
            guild_id = ctx.guild.id

            await ctx.message.delete()
            # if the user that ran the command is the same as member, then exit the function
            if ctx.author.id == member.id:
                await self.discord_helper.sendEmbed(ctx.channel,
                self.settings.get_string(guild_id, "error"),
                self.settings.get_string(guild_id, "taco_self_gift_message", user=ctx.author.mention),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT)
                return

            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reason_msg = self.settings.get_string(guild_id, "taco_reason_default")
            if reason:
                reason_msg = f"{reason}"

            await self.discord_helper.sendEmbed(ctx.channel,
                self.settings.get_string(guild_id, "taco_give_title"),
                # 	"taco_gift_success": "{{user}}, You gave {touser} {amount} {taco_word} 🌮.\n\n{{reason}}",
                self.settings.get_string(guild_id, "taco_gift_success", user=ctx.author.mention, touser=member.mention, amount=amount, taco_word=tacos_word, reason=reason_msg),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT)

            await self.discord_helper.taco_give_user(guild_id, ctx.author, member, reason_msg, tacotypes.TacoTypes.CUSTOM, taco_amount=amount )


        except Exception as e:
            self.log.error(ctx.guild.id, "tacos.give", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @tacos.command()
    async def count(self, ctx):
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id
                await ctx.message.delete()
            # get taco count for message author
            taco_count = self.db.get_tacos_count(guild_id, ctx.author.id)
            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if taco_count is None:
                taco_count = 0
            if taco_count == 0 or taco_count > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")
            await self.discord_helper.sendEmbed(ctx.channel,
                self.settings.get_string(guild_id, "taco_count_title"),
                self.settings.get_string(guild_id, "taco_count_message", user=ctx.author.mention, count=taco_count, taco_word=tacos_word),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT)
        except Exception as e:
            await ctx.message.delete()
            self.log.error(ctx.guild.id, "tacos.count", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @tacos.command()
    @commands.guild_only()
    async def gift(self, ctx, member: discord.Member, amount: int, *, reason: str = None):
        try:
            guild_id = ctx.guild.id
            # get taco count for message author
            await ctx.message.delete()
            taco_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not taco_settings:
                # raise exception if there are no tacos settings
                self.log.error(guild_id, "tacos.on_message", f"No tacos settings found for guild {guild_id}")
                await self.discord_helper.notify_bot_not_initialized(ctx, "tacos")
                return

            # if the user that ran the command is the same as member, then exit the function
            if ctx.author.id == member.id:
                await self.discord_helper.sendEmbed(ctx.channel,
                    self.settings.get_string(guild_id, "error"),
                    self.settings.get_string(guild_id, "taco_self_gift_message", user=ctx.author.mention),
                    footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                    delete_after=self.SELF_DESTRUCT_TIMEOUT)
                return
            max_gift_tacos = taco_settings.get("max_gift_tacos", 10)
            max_gift_taco_timespan = taco_settings.get("max_gift_taco_timespan", 86400)
            # get the total number of tacos the user has gifted in the last 24 hours
            total_gifted = self.db.get_total_gifted_tacos(ctx.guild.id, ctx.author.id, max_gift_taco_timespan)
            remaining_gifts = max_gift_tacos - total_gifted

            tacos_word = self.settings.get_string(guild_id, "taco_plural")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_singular")


            if remaining_gifts <= 0:
                await self.discord_helper.sendEmbed(ctx.channel,
                    self.settings.get_string(guild_id, "taco_gift_title"),
                    self.settings.get_string(guild_id, "taco_gift_maximum", max=max_gift_tacos, taco_word=tacos_word),
                    delete_after=30)
                return
            if amount <= 0 or amount > remaining_gifts:
                await self.discord_helper.sendEmbed(ctx.channel,
                    self.settings.get_string(guild_id, "taco_gift_title"),
                    self.settings.get_string(guild_id, "taco_gift_limit_exceeded", user=ctx.author.mention, remaining=remaining_gifts, taco_word=tacos_word),
                    footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                    delete_after=self.SELF_DESTRUCT_TIMEOUT)
                return

            reason_msg = self.settings.get_string(guild_id, "taco_reason_default")
            if reason:
                reason_msg = f"{reason}"

            self.db.add_taco_gift(ctx.guild.id, ctx.author.id, amount)
            await self.discord_helper.sendEmbed(ctx.channel,
                self.settings.get_string(guild_id, "taco_gift_title"),
                self.settings.get_string(guild_id, "taco_gift_success", user=ctx.message.author.mention, touser=member.mention, amount=amount, taco_word=tacos_word, reason=reason_msg),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT)

            await self.discord_helper.taco_give_user(guild_id, ctx.author, member, reason_msg, tacotypes.TacoTypes.CUSTOM, taco_amount=amount )

        except Exception as e:
            self.log.error(ctx.guild.id, "tacos.gift", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)


    # @tacos.error()
    # async def tacos_error(self, ctx, error):
    #     _method = inspect.stack()[1][3]
    #     if isinstance(error, discord.errors.NotFound):
    #         self.log.warn(ctx.guild.id, _method , str(error), traceback.format_exc())
    #     else:
    #         self.log.error(ctx.guild.id, _method , str(error), traceback.format_exc())
    #         await self.discord_helper.notify_of_error(ctx)

    @commands.Cog.listener()
    async def on_message(self, message):
        _method = inspect.stack()[0][3]
        member = message.author
        try:
            # if we are in a guild
            if message.guild:
                guild_id = message.guild.id

                if member.bot:
                    return

                if message.type == discord.MessageType.premium_guild_subscription:
                    # add tacos to user that boosted the server
                    await self.discord_helper.taco_give_user(guild_id, self.bot.user, member,
                        self.settings.get_string(guild_id, "taco_reason_boost"),
                        tacotypes.TacoTypes.BOOST )
                    return

                if message.type == discord.MessageType.default:
                    try:
                        if message.reference is not None:
                            ref = message.reference.resolved
                            if ref is None:
                                return
                            if ref.author == message.author or ref.author == self.bot.user:
                                self.log.debug(guild_id, f"tacos.{_method}", f"Ignoring message reference from {ref.author}")
                                return
                            # it is a reply to another user
                            await self.discord_helper.taco_give_user(guild_id, self.bot.user, member,
                                self.settings.get_string(guild_id, "taco_reason_reply", user=ref.author.name),
                                tacotypes.TacoTypes.REPLY )

                    except Exception as e:
                        self.log.error(guild_id, f"tacos.{_method}", str(e), traceback.format_exc())
                        return

            # if we are in a DM
            else:
                return
        except Exception as ex:
            self.log.error(member.guild.id, f"tacos.{_method}", str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:
            if payload.event_type != 'REACTION_ADD':
                return

            taco_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not taco_settings:
                # raise exception if there are no tacos settings
                self.log.error(guild_id, "tacos.on_raw_reaction_add", f"No tacos settings found for guild {guild_id}")
                return

            reaction_emoji = taco_settings.get("reaction_emoji", "🌮")

            self.log.debug(guild_id, f"tacos.{_method}", f"{payload.emoji.name} added to {payload.message_id}")
            if str(payload.emoji) == reaction_emoji:
                user = await self.discord_helper.get_or_fetch_user(payload.user_id)
                channel = await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                # if the message is from a bot, or reacted by the author, ignore it
                if message.author.bot or message.author.id == user.id:
                    return

                has_reacted = self.db.get_taco_reaction(guild_id, user.id, channel.id, message.id)
                if has_reacted:
                    # log that the user has already reacted
                    # self.log.debug(guild_id, f"tacos.{_method}", f"{user} has already reacted to {message.id} so no tacos given.")
                    return



                reaction_count = taco_settings.get("reaction_count", 1)
                # reaction_reward_count = taco_settings["reaction_reward_count"]

                max_gift_tacos = taco_settings.get("max_gift_tacos", 10)
                max_gift_taco_timespan = taco_settings.get("max_gift_taco_timespan", 86400)
                # get the total number of tacos the user has gifted in the last 24 hours
                total_gifted = self.db.get_total_gifted_tacos(guild_id, user.id, max_gift_taco_timespan)
                # log the total number of tacos the user has gifted
                # self.log.debug(guild_id, f"tacos.{_method}", f"{user} has gifted {total_gifted} tacos in the last {max_gift_taco_timespan} seconds.")
                remaining_gifts = max_gift_tacos - total_gifted

                # self.log.debug(guild_id, f"tacos.{_method}", f"🌮 adding taco to user {message.author.name}")
                # track the user's taco reaction
                self.db.add_taco_reaction(guild_id, user.id, channel.id, message.id)
                # # give the user the reaction reward tacos
                await self.discord_helper.taco_give_user(guild_id, user, message.author,
                    self.settings.get_string(guild_id, "taco_reason_react", user=message.author.name),
                    tacotypes.TacoTypes.REACT_REWARD )

                if reaction_count <= remaining_gifts:
                    # self.log.debug(guild_id, f"tacos.{_method}", f"🌮 adding taco to user {user.name}")
                    # track that the user has gifted tacos via reactions
                    self.db.add_taco_gift(guild_id, user.id, reaction_count)
                    # give taco giver tacos too
                    await self.discord_helper.taco_give_user(guild_id, self.bot.user, user,
                        self.settings.get_string(guild_id, "taco_reason_react", user=message.author.name),
                        tacotypes.TacoTypes.REACTION )
                # else:
                #     # log that the user cannot gift anymore tacos via reactions
                #     self.log.debug(guild_id, f"tacos.{_method}", f"{user} cannot gift anymore tacos. remaining gifts: {remaining_gifts}")
        except Exception as ex:
            self.log.error(guild_id, f"tacos.{_method}", str(ex), traceback.format_exc())

async def setup(bot):
    await bot.add_cog(Tacos(bot))
