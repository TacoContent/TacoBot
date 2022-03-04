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
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider

import inspect

class Tacos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "tacos"

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
    async def help(self, ctx):
        # todo: add help command
        await self.discord_helper.sendEmbed(ctx.channel, "Help", f"Use `.taco help tacos` for help on this topic.", delete_after=30)
        # only delete if the message is in a guild channel
        if ctx.guild:
            await ctx.message.delete()

    # create command called remove_all_tacos that asks for the user
    @tacos.command(aliases=['purge'])
    @commands.has_permissions(administrator=True)
    async def remove_all_tacos(self, ctx, user: discord.Member, *, reason: str = None):
        try:
            guild_id = ctx.guild.id
            await ctx.message.delete()
            self.db.remove_all_tacos(guild_id, user.id)
            reason_msg = reason if reason else "No reason given."
            await self.discord_helper.sendEmbed(ctx.channel, "Removed All Tacos", f"{user.mention} has lost all their tacos.", delete_after=30)
            await self.discord_helper.taco_purge_log(ctx.guild.id, user, ctx.author, reason_msg)

        except Exception as e:
            await self.discord_helper.sendEmbed(ctx.channel, "Error", f"{e}", delete_after=30)
            await ctx.message.delete()

    @tacos.command()
    @commands.has_permissions(administrator=True)
    async def give(self, ctx, member: discord.Member, amount: int, *, reason: str = None):
        try:
            guild_id = ctx.guild.id

            await ctx.message.delete()
            # if the user that ran the command is the same as member, then exit the function
            if ctx.author.id == member.id:
                await self.discord_helper.sendEmbed(ctx.channel, "Error", f"You can't give yourself tacos.", delete_after=30)
                return
            tacos_word = "taco"
            if amount > 1:
                tacos_word = "tacos"

            self.db.add_tacos(guild_id, member.id, amount)
            reason_msg = f"just being Awesome!"
            if reason:
                reason_msg = f"{reason}"

            await self.discord_helper.sendEmbed(ctx.channel, "Give Tacos", f"{member.mention} has been given {amount} {tacos_word} 🌮.\n\n{reason_msg}", delete_after=30)
            taco_count = self.db.get_tacos_count(ctx.guild.id, member.id)
            await self.discord_helper.tacos_log(ctx.guild.id, member, ctx.author, amount, taco_count, reason_msg)

        except Exception as e:
            self.log.error(ctx.guild.id, "tacos.give", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @tacos.command()
    async def count(self, ctx):
        try:
            # get taco count for message author
            taco_count = self.db.get_tacos_count(ctx.guild.id, ctx.author.id)
            tacos_word = "taco"
            if taco_count is None:
                taco_count = 0
            if taco_count == 0 or taco_count > 1:
                tacos_word = "tacos"
            await ctx.message.delete()
            await self.discord_helper.sendEmbed(ctx.channel, "Taco Count", f"{ctx.author.mention}, You have {taco_count} {tacos_word} 🌮.\n\nThis message will delete in 30 seconds.", delete_after=30)
        except Exception as e:
            await ctx.message.delete()
            self.log.error(ctx.guild.id, "tacos.count", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @tacos.command()
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
                await self.discord_helper.sendEmbed(ctx.channel, "Error", f"You can't gift yourself tacos.", delete_after=30)
                return
            max_gift_tacos = taco_settings["max_gift_tacos"]
            max_gift_taco_timespan = taco_settings["max_gift_taco_timespan"]
            # get the total number of tacos the user has gifted in the last 24 hours
            total_gifted = self.db.get_total_gifted_tacos(ctx.guild.id, ctx.author.id, max_gift_taco_timespan)
            remaining_gifts = max_gift_tacos - total_gifted
            if remaining_gifts <= 0:
                await self.discord_helper.sendEmbed(ctx.channel, "Error", f"You have reached the maximum amount of gifts you can give. You can only give {max_gift_tacos} tacos per 24 hours.", delete_after=30)
                return
            if amount <= 0 or amount > remaining_gifts:
                await self.discord_helper.sendEmbed(ctx.channel, "Gift Tacos", f"{ctx.author.mention}, You can only gift between 1 and {remaining_gifts} tacos.", delete_after=30)
                return

            tacos_word = "taco"
            if amount > 1:
                tacos_word = "tacos"
            reason_msg = f"For just being Awesome!"
            if reason:
                reason_msg = f"{reason}"

            self.db.add_tacos(ctx.guild.id, member.id, amount)
            self.db.add_taco_gift(ctx.guild.id, ctx.author.id, amount)

            await self.discord_helper.sendEmbed(ctx.channel, "Gift Tacos", f"{ctx.message.author.mention}, You gave {member.mention} {amount} {tacos_word} 🌮.\n\n{reason_msg}\n\nThis message will delete in 30 seconds.", delete_after=30)
            taco_count = self.db.get_tacos_count(ctx.guild.id, member.id)
            await self.discord_helper.tacos_log(ctx.guild.id, member, ctx.author, amount, taco_count, reason_msg)
        except Exception as e:
            self.log.error(ctx.guild.id, "tacos.gift", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            _method = inspect.stack()[0][3]
            # if we are in a guild
            if message.guild:
                guild_id = message.guild.id
                member = message.author

                if member.bot:
                    return

                taco_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
                if not taco_settings:
                    # raise exception if there are no tacos settings
                    self.log.error(guild_id, "tacos.on_message", f"No tacos settings found for guild {guild_id}")
                    await self.discord_helper.notify_bot_not_initialized(message, "tacos")
                    return

                if message.type == discord.MessageType.premium_guild_subscription:
                    # add tacos to user that boosted the server
                    taco_boost_amount = taco_settings["boost_count"]
                    self.log.debug(member.guild.id, _method, f"{member} boosted the server")
                    taco_count = self.db.add_tacos(guild_id, member.id, taco_boost_amount)

                    await self.discord_helper.tacos_log(guild_id, member, self.bot.user, taco_boost_amount, taco_count, "boosting the server")
            # if we are in a DM
            else:
                return
        except Exception as ex:
            self.log.error(member.guild.id, _method, str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # remove all tacos from the user
        try:
            if member.bot:
                return
            _method = inspect.stack()[0][3]
            self.log.debug(member.guild.id, _method, f"{member} left the server")
            self.db.remove_all_tacos(member.guild.id, member.id)
        except Exception as ex:
            self.log.error(member.guild.id, _method, str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        _method = inspect.stack()[0][3]
        guild_id = member.guild.id
        try:
            if member.bot:
                return
            taco_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not taco_settings:
                # raise exception if there are no tacos settings
                self.log.error(guild_id, "tacos.on_member_join", f"No tacos settings found for guild {guild_id}")
                return

            join_count = taco_settings["join_count"]
            self.log.info(guild_id, _method, f"{member} joined the server")
            taco_count = self.db.add_tacos(guild_id, member.id, join_count)
            await self.discord_helper.tacos_log(guild_id, member, self.bot.user, join_count, taco_count, "joining the server")
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:
            if payload.event_type != 'REACTION_ADD':
                return

            self.log.debug(guild_id, _method, f"{payload.emoji.name} added to {payload.message_id}")
            if str(payload.emoji) == '🌮':
                user = await self.discord_helper.get_or_fetch_user(payload.user_id)
                channel = await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                # if the message is from a bot, or reacted by the author, ignore it
                if message.author.bot or message.author.id == user.id:
                    return

                has_reacted = self.db.get_taco_reaction(guild_id, user.id, channel.id, message.id)
                if has_reacted:
                    # log that the user has already reacted
                    self.log.debug(guild_id, _method, f"{user} has already reacted to {message.id} so no tacos given.")
                    return

                taco_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
                if not taco_settings:
                    # raise exception if there are no tacos settings
                    self.log.error(guild_id, "tacos.on_raw_reaction_add", f"No tacos settings found for guild {guild_id}")
                    return

                reaction_count = taco_settings["reaction_count"]
                reaction_reward_count = taco_settings["reaction_reward_count"]

                max_gift_tacos = taco_settings["max_gift_tacos"]
                max_gift_taco_timespan = taco_settings["max_gift_taco_timespan"]
                # get the total number of tacos the user has gifted in the last 24 hours
                total_gifted = self.db.get_total_gifted_tacos(guild_id, user.id, max_gift_taco_timespan)
                # log the total number of tacos the user has gifted
                self.log.debug(guild_id, _method, f"{user} has gifted {total_gifted} tacos in the last {max_gift_taco_timespan} seconds.")
                remaining_gifts = max_gift_tacos - total_gifted

                self.log.debug(guild_id, _method, f"🌮 adding taco to user {message.author.name}")
                # give the user the reaction reward tacos
                taco_count = self.db.add_tacos(guild_id, message.author.id, reaction_count)
                # track the user's taco reaction
                self.db.add_taco_reaction(guild_id, user.id, channel.id, message.id)
                self.log.debug(guild_id, _method, f"🌮 added taco to user {message.author.name} successfully")
                await self.discord_helper.tacos_log(guild_id, message.author, user, reaction_count, taco_count, f"reacting to {message.author.name}'s message with a 🌮")

                if reaction_count <= remaining_gifts:
                    self.log.debug(guild_id, _method, f"🌮 adding taco to user {user.name}")
                    # track that the user has gifted tacos via reactions
                    self.db.add_taco_gift(guild_id, user.id, reaction_count)
                    # give taco giver tacos too
                    taco_count = self.db.add_tacos(guild_id, user.id, reaction_reward_count)
                    self.log.debug(guild_id, _method, f"🌮 added taco to user {user.name} successfully")
                    await self.discord_helper.tacos_log(guild_id, user, self.bot.user, reaction_reward_count, taco_count, f"reacting to {message.author.name}'s message with a 🌮")
                else:
                    # log that the user cannot gift anymore tacos via reactions
                    self.log.debug(guild_id, _method, f"{user} cannot gift anymore tacos. remaining gifts: {remaining_gifts}")
            else:
                self.log.debug(guild_id, _method, f"{payload.emoji} not a taco")
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())

    # @setup.error
    # async def info_error(self, ctx, error):
    #     _method = inspect.stack()[1][3]
    #     if isinstance(error, discord.errors.NotFound):
    #         self.log.warn(ctx.guild.id, _method , str(error), traceback.format_exc())
    #     else:
    #         self.log.error(ctx.guild.id, _method , str(error), traceback.format_exc())

def setup(bot):
    bot.add_cog(Tacos(bot))
