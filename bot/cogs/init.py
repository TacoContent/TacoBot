import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import math
import inspect

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


class InitHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "init.__init__", "Initialized")

    @commands.group()
    @commands.has_permissions(administrator=True)
    async def init(self, ctx):
        if ctx.invoked_subcommand is None:
            if not ctx.guild:
                return
            guild_id = ctx.guild.id
            await ctx.message.delete()

            await self.prefix_action(ctx, delete_message=False)
            await self.paypost_action(ctx, delete_message=False)
            await self.suggestions_action(ctx, delete_message=False)
            await self.tacos_action(ctx, delete_message=False)
            await self.restricted_action(ctx, delete_message=False)

        else:
            pass
    @init.command()
    @commands.has_permissions(administrator=True)
    async def prefix(self, ctx: ComponentContext):
        await self.prefix_action(ctx, delete_message=True)

    async def prefix_action(self, ctx: ComponentContext, delete_message=True):
        try:
            if not ctx.guild:
                return
            guild_id = ctx.guild.id

            taco_settings = self.settings.get_settings(self.db, guild_id, "tacobot")
            if not taco_settings:
                self.db.add_settings(guild_id, "tacobot", {
                    "command_prefixes": [ ".taco ", "?taco ", "!taco " ],
                })
            if delete_message:
                await ctx.message.delete()
        except Exception as e:
            self.log.error(guild_id, "init.prefix", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)
        try:
            if not ctx.guild:
                return
            guild_id = ctx.guild.id

            taco_settings = self.settings.get_settings(self.db, guild_id, "tacobot")
            if not taco_settings:
                self.db.add_settings(guild_id, "tacobot", {
                    "command_prefixes": [ ".taco ", "?taco ", "!taco " ],
                })
            if delete_message:
                await ctx.message.delete()
        except Exception as e:
            self.log.error(guild_id, "init.prefix", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @init.group()
    @commands.has_permissions(administrator=True)
    async def restricted(self, ctx: ComponentContext):
        if ctx.invoked_subcommand is None:
            if not ctx.guild:
                return
            guild_id = ctx.guild.id
            await ctx.message.delete()

            await self.restricted_action(ctx, delete_message=False)
        else:
            pass


    async def restricted_action(self, ctx: ComponentContext, delete_message=True):
        if ctx.invoked_subcommand is None:
            try:
                if not ctx.guild:
                    return
                guild_id = ctx.guild.id
                if delete_message:
                    await ctx.message.delete()
                post_settings = self.settings.get_settings(self.db, guild_id, "restricted")
                if not post_settings:
                    self.db.add_settings(guild_id, "restricted", {
                        "channels": [ ],
                    })
                add_another_channel = True
                while add_another_channel:
                    add_another_channel = await self.discord_helper.ask_yes_no(ctx, ctx.channel, "Restricted", "Do you want to configure a channel to be restricted what can be posted?")
                    if add_another_channel:
                        # ask for channel from list
                        channel = await self.discord_helper.ask_channel(ctx, "Restricted", "Please select a channel to configure as restricted.")
                        if channel:
                            await self.restricted_add_action(ctx, channel, delete_message=False)
                        else:
                            await self.discord_helper.sendEmbed(ctx.channel, "Restricted", "The channel selected was not found.", color=0xFF0000, delete_after=20)
            except Exception as e:
                self.log.error(guild_id, "init.restricted", str(e), traceback.format_exc())
                await self.discord_helper.notify_of_error(ctx)
        else:
            pass

    @restricted.command()
    @commands.has_permissions(administrator=True)
    async def restricted_add(self, ctx: ComponentContext, channel: discord.TextChannel):
        await self.restricted_add_action(ctx, channel)

    async def restricted_add_action(self, ctx: ComponentContext, channel: discord.TextChannel, delete_message=True):
        try:
            if not ctx.guild:
                return
            guild_id = ctx.guild.id
            if delete_message:
                await ctx.message.delete()
            restricted_settings = self.settings.get_settings(self.db, guild_id, "restricted")
            if not restricted_settings:
                self.db.add_settings(guild_id, "restricted", {
                    "channels": [ ],
                })
            allow_pattern = await self.discord_helper.ask_text(ctx, ctx.channel, "Restricted", "Please enter a pattern to allow.")
            if not allow_pattern:
                return
            deny_message = await self.discord_helper.ask_text(ctx, ctx.channel, "Restricted", "Please enter the message that will be sent if the message is denied.")
            if not deny_message:
                deny_message = "You are not allowed to send that in this channel."
            r_channels = [ c for c in restricted_settings["channels"] if c["channel_id"] == str(channel.id) ]

            # if we have settings already, remove it to add the new one
            if len(r_channels) > 0:
                restricted_settings["channels"].remove(r_channels[0])


            restricted_settings["channels"].append({
                "id": channel.id,
                "allowed": allow_pattern,
                "denied": [],
                "deny_message": deny_message,
                "exempt" : []
            })

            self.db.add_settings(guild_id, "restricted", restricted_settings)
            fields = [
                { "name": "Channel", "value": channel.mention, "inline": True },
                { "name": "Allow Pattern", "value": allow_pattern, "inline": True },
                { "name": "Deny Message", "value": deny_message, "inline": True },
            ]
            await self.discord_helper.sendEmbed(ctx.channel, "Restricted", "Restricted channel added.", fields=fields, color=0x00FF00, delete_after=20)
        except Exception as e:
            self.log.error(guild_id, "init.restricted_add", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @init.group()
    @commands.has_permissions(administrator=True)
    async def paypost(self, ctx: ComponentContext):
        if ctx.invoked_subcommand is None:
            if not ctx.guild:
                return
            guild_id = ctx.guild.id
            await ctx.message.delete()

            await self.paypost_action(ctx, delete_message=False)
        else:
            pass

    async def paypost_action(self, ctx: ComponentContext, delete_message=True):
        if ctx.invoked_subcommand is None:
            try:
                if not ctx.guild:
                    return
                guild_id = ctx.guild.id
                if delete_message:
                    await ctx.message.delete()
                post_settings = self.settings.get_settings(self.db, guild_id, "tacopost")
                if not post_settings:
                    self.db.add_settings(guild_id, "tacopost", {
                        "channels": [ ],
                    })
                add_another_channel = True
                while add_another_channel:
                    add_another_channel = await self.discord_helper.ask_yes_no(ctx, ctx.channel, "Pay to Post", "Do you want to configure a channel to require paying to post?")
                    if add_another_channel:
                        # ask for channel from list
                        channel = await self.discord_helper.ask_channel(ctx, "Pay to Post", "Please select a channel to require paying to post.")
                        if channel:
                            await self.paypost_add_action(ctx, channel, delete_message=False)
                        else:
                            await self.discord_helper.sendEmbed(ctx.channel, "Pay to Post", "The channel selected was not found.", color=0xFF0000, delete_after=20)
            except Exception as e:
                self.log.error(guild_id, "init.paypost", str(e), traceback.format_exc())
                await self.discord_helper.notify_of_error(ctx)
        else:
            pass

    @paypost.command(aliases=["add-channel"])
    @commands.has_permissions(administrator=True)
    async def add(self, ctx: ComponentContext, channel: discord.TextChannel):
        await self.paypost_add_action(ctx, channel, delete_message=True)

    async def paypost_add_action(self, ctx: ComponentContext, channel: discord.TextChannel, delete_message=True):
        try:
            if not ctx.guild:
                return
            guild_id = ctx.guild.id
            if delete_message:
                await ctx.message.delete()
            post_settings = self.settings.get_settings(self.db, guild_id, "tacopost")
            if not post_settings:
                self.db.add_settings(guild_id, "tacopost", {
                    "channels": [ ],
                })
            cost = await self.discord_helper.ask_number(ctx, "Pay to Post", "How much do you want to charge per post?", min_value=0, max_value=100000)
            if cost is None:
                return
            ask_exempt = await self.discord_helper.ask_yes_no(ctx, ctx.channel, "Pay to Post", "Do you want to exempt a role from paying to post in this channel?")
            exempt_roles = []
            ask_exempt = True
            while ask_exempt:
                if ask_exempt:
                    excluded_roles = [ r for r in ctx.guild.roles if r.name.startswith("@") or r.name.startswith("LFG-") ]
                    exempt_role = await self.discord_helper.ask_role_list(ctx, "Select Roles", "Select roles to exempt from paying to post in this channel", allow_none=True, exclude_roles=excluded_roles)
                    if exempt_role:
                        exempt_roles.append(str(exempt_role.id))
                        ask_exempt = await self.discord_helper.ask_yes_no(ctx, ctx.channel, "Pay to Post", "Do you want to exempt another role from paying to post in this channel?")
                    else:
                        ask_exempt = False
            if str(channel.id) in [ c.id for c in post_settings["channels"] ]:
                # remove the channel from the list
                post_settings["channels"] = [ c for c in post_settings["channels"] if c.id != str(channel.id) ]

            post_settings["channels"].append( { "id": str(channel.id), "cost": cost, "exempt": exempt_roles } )
            self.db.add_settings(guild_id, "tacopost", post_settings)
        except Exception as e:
            self.log.error(guild_id, "init.paypost.add", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @init.command()
    @commands.has_permissions(administrator=True)
    async def suggestions(self, ctx: ComponentContext):
        await self.suggestions_action(ctx, delete_message=True)

    async def suggestions_action(self, ctx: ComponentContext, delete_message=True):
        try:
            if not ctx.guild:
                return
            if delete_message:
                await ctx.message.delete()
            guild_id = ctx.guild.id
            suggestions_settings = self.settings.get_settings(self.db, guild_id, "suggestions")
            if not suggestions_settings:
                self.db.add_settings(guild_id, "suggestions", {
                    "channels": [ ],
                })
                # await self.discord_helper.ask_channel(ctx, "Pay to Post", "Select Channel to add for Pay to Post", allow_none=True)
            add_another_channel = True
            first_ask = True
            while add_another_channel:
                if first_ask:
                    first_ask = False
                    another = "a "
                else:
                    another = "another "
                add_another_channel = await self.discord_helper.ask_yes_no(ctx, ctx.channel, "Suggestions", f"Do you want to configure {another} channel to receive suggestions?")
                if add_another_channel:
                    # ask for channel from list
                    settings_channel = await self.discord_helper.ask_channel(ctx, "Suggestions", "Please select a channel to receive suggestions.")
                    if settings_channel:
                        channel_settings = [ c for c in suggestions_settings["channels"] if c["id"] == str(settings_channel.id) ]

                        if channel_settings and len(channel_settings) > 0:
                            channel_settings = channel_settings[0]
                            suggestions_settings["channels"].remove(channel_settings)
                            channel_settings['id'] = str(settings_channel.id)
                        else:
                            channel_settings = {
                                'id': str(settings_channel.id),
                                'vote_up_emoji': '🔼',
                                'vote_down_emoji': '🔽',
                                'vote_neutral_emoji': '🟦',
                                'admin_approve_emoji': '✅',
                                'admin_reject_emoji': '❌',
                                'admin_consider_emoji': '👀',
                                'admin_implemented_emoji': '🟢',
                                'admin_close_emoji': '🔒',
                                'admin_delete_emoji': '⛔'
                            }
                        add_log_channel = await self.discord_helper.ask_yes_no(ctx, ctx.channel, "Suggestions", "Do you want to add a log channel for this channel?")
                        log_channel = None
                        if add_log_channel:
                            log_channel = await self.discord_helper.ask_channel(ctx, "Suggestions", "Please select a channel to log closed suggestions to.")
                            if log_channel:
                                channel_settings['log_channel_id'] = str(log_channel.id)
                            else:
                                channel_settings['log_channel_id'] = None
                        suggestions_settings["channels"].append(channel_settings)
                        self.db.add_settings(guild_id, "suggestions", suggestions_settings)
                        await self.discord_helper.sendEmbed(ctx.channel, "Suggestions", "Channel added to suggestions.", color=0x00FF00, delete_after=20)
                    else:
                        await self.discord_helper.sendEmbed(ctx.channel, "Suggestions", "The channel selected was not found.", color=0xFF0000, delete_after=20)

        except Exception as e:
            self.log.error(guild_id, "init.suggestions", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @init.command()
    @commands.has_permissions(administrator=True)
    async def tacos(self, ctx: ComponentContext):
        await self.tacos_action(ctx, delete_message=True)

    async def tacos_action(self, ctx: ComponentContext, delete_message=True):
        try:
            if not ctx.guild:
                return
            if delete_message:
                await ctx.message.delete()
            guild_id = ctx.guild.id
            tacos_settings = self.settings.get_settings(self.db, guild_id, "tacos")
            edit_settings = tacos_settings is None
            if tacos_settings:
                edit_settings = await self.discord_helper.ask_yes_no(ctx, ctx.channel, "Edit Tacos Settings", "Do you want to edit tacos settings?")

            if edit_settings:
                log_channel = await self.discord_helper.ask_channel(ctx, "Select Taco Log Channel", "Select Channel use for Taco Logs", allow_none=False)
                self.db.add_settings(guild_id, "tacos", {
                    "taco_log_channel_id": str(log_channel.id),
                    "max_gift_tacos": 10,
                    "max_gift_taco_timespan": 86400,
                    "reaction_count": 1,
                    "join_count": 5,
                    "boost_count": 100,
                    "reaction_reward_count": 1,
                    "suggest_count": 5,
                    "invite_count": 25,
                })

        except Exception as e:
            self.log.error(guild_id, "init.tacos", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @init.command()
    @commands.has_permissions(administrator=True)
    async def help(self, ctx):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
            await ctx.message.delete()
        await self.discord_helper.sendEmbed(ctx.channel,
            self.settings.get_string(guild_id, "help_title", bot_name=self.settings.name),
            self.settings.get_string(guild_id, "help_module_message", bot_name=self.settings.name, command="init"),
            footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
            color=0xff0000, delete_after=30)
        pass

def setup(bot):
    bot.add_cog(InitHandler(bot))
