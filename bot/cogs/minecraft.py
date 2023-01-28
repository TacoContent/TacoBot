# https://crafthead.net/armor/body/<uuid>
# https://playerdb.co/
# https://playerdb.co/api/player/minecraft/<name|uuid>

import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import requests

from discord.ext.commands.cooldowns import BucketType
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import (
    create_button,
    create_actionrow,
    create_select,
    create_select_option,
    wait_for_component,
)
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
from .lib import tacotypes

import inspect


class Minecraft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "minecraft"
        self.SELF_DESTRUCT_TIMEOUT = 30
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "minecraft.__init__", "Initialized")

    # disable user from whitelist if they leave the discord
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            if not self.is_user_whitelisted(member.id):
                return
            mc_user = self.db.get_minecraft_user(member.id)
            if not mc_user:
                return

            self.log.debug(member.guild.id, "minecraft.on_member_remove", f"Member {member.name} has left the server")
            self.db.whitelist_minecraft_user(member.id, mc_user['username'], mc_user['uuid'], False)

        except Exception as e:
            self.log.error(member.guild.id, "minecraft.on_member_remove", str(e), traceback.format_exc())

    @commands.group(name="minecraft", invoke_without_command=True)
    async def minecraft(self, ctx: ComponentContext):
        if ctx.invoked_subcommand is not None:
            return
        guild_id = 0
        try:
            await self.status(ctx)
        except Exception as e:
            self.log.error(guild_id, "minecraft.minecraft", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    async def status(self, ctx):
        guild_id = 0
        try:
            if ctx.guild:
                await ctx.message.delete()
                guild_id = ctx.guild.id


            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(guild_id, "minecraft.status", f"No minecraft settings found for guild {guild_id}")
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, "minecraft.status", f"minecraft is disabled for guild {guild_id}")
                return

            if not self.is_user_whitelisted(ctx.author.id):
                await self.discord_helper.sendEmbed(ctx.channel,
                    title="Minecraft Whitelist",
                    message=f"You are not yet whitelisted. Run `.taco minecraft whitelist` to whitelist your account. Only one account can be whitelisted per discord user.",
                    delete_after=self.SELF_DESTRUCT_TIMEOUT)
                return

            result = requests.get(f"http://andeddu.bit13.local:10070/tacobot/minecraft/status")
            if result.status_code != 200:
                # Need to notify of an error
                self.log.warn(guild_id, "minecraft.status", f"Failed to get minecraft status ({result.status_code} - {result.text})")
                raise Exception("Failed to get minecraft status ({result.status_code} - {result.text})")

            data = result.json()
            # get users uuid for minecraft username
            if not data["success"]:
                self.log.warn(guild_id, "minecraft.status", f"Failed to get minecraft status")

            fields = [
                { "name": "Host Address", "value": f"`{cog_settings['server']}`", "inline": False },
                { "name": "Players Online/Slots", "value": f"{data['players']['online']}/{data['players']['max']}", "inline": False },
                { "name": "Version", "value": f"{data['version']}", "inline": False },
                { "name": "Forge Version", "value": f"{cog_settings['forge_version']}", "inline": False },
                { "name": "Mods", "value": f"------", "inline": False },
            ]

            for m in cog_settings["mods"]:
                fields.append({ "name": f"{m['name']}", "value": f"{m['version']}", "inline": True })

            await self.discord_helper.sendEmbed(ctx.channel,
                title="Minecraft Server Status",
                message=f"{data['title']}\n\nFor information on how to install see: <{cog_settings['help']}>",
                fields=fields,
                delete_after=self.SELF_DESTRUCT_TIMEOUT)

        except Exception as e:
            self.log.error(guild_id, "minecraft.status", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @minecraft.command()
    @commands.guild_only()
    async def whitelist(self, ctx: ComponentContext):
        guild_id = 0
        try:
            if ctx.guild:
                await ctx.message.delete()
                guild_id = ctx.guild.id

            if self.is_user_whitelisted(ctx.author.id):
                await self.discord_helper.sendEmbed(ctx.channel,
                    title="Minecraft Whitelist",
                    message=f"You are already whitelisted. Message an admin if you need to remove an account. Only one account can be whitelisted per discord user.",
                    delete_after=self.SELF_DESTRUCT_TIMEOUT)
                return

            # try DM first
            try:
                _ctx = self.discord_helper.create_context(
                    self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild
                )
                mc_username = await self.discord_helper.ask_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "minecraft_ask_username_title"),
                    self.settings.get_string(guild_id, "minecraft_ask_username_message"),
                    timeout=60 * 5,
                )
            except discord.Forbidden:
                _ctx = ctx
                mc_username = await self.discord_helper.ask_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "minecraft_ask_username_title"),
                    self.settings.get_string(guild_id, "minecraft_ask_username_message"),
                    timeout=60 * 5,
                )

            if mc_username is None or mc_username.lower() == "cancel":
                return

            # cog_settings = self.get_cog_settings(guild_id)
            # if not cog_settings:
            #     self.log.warn(guild_id, "minecraft.whitelist", f"No minecraft settings found for guild {guild_id}")
            #     return
            # if not cog_settings.get("enabled", False):
            #     self.log.debug(guild_id, "minecraft.whitelist", f"minecraft is disabled for guild {guild_id}")
            #     return

            # {
            #     "code": "player.found",
            #     "message": "Successfully found player by given ID.",
            #     "data": {
            #         "player": {
            #             "meta": {
            #                 "name_history": [
            #                     {"name": "IcamalotI"},
            #                     {"name": "DarthMinos", "changedToAt": 1577518972000},
            #                 ]
            #             },
            #             "username": "DarthMinos",
            #             "id": "1b313cdd-7465-4227-95aa-ca5503beba85",
            #             "raw_id": "1b313cdd7465422795aaca5503beba85",
            #             "avatar": "https://crafthead.net/avatar/1b313cdd7465422795aaca5503beba85",
            #         }
            #     },
            #     "success": true,
            # }
            result = requests.get(f"https://playerdb.co/api/player/minecraft/{mc_username}")
            if result.status_code != 200:
                # Need to notify of an error
                self.log.warn(guild_id, "minecraft.whitelist", f"Failed to find player {mc_username}")
                raise Exception("Failed to find player {mc_username} from playerdb.co api call ({result.status_code} - {result.text})")

            data = result.json()
            # get users uuid for minecraft username
            if not data["success"] or data["code"] != "player.found":
                self.log.warn(guild_id, "minecraft.whitelist", f"Failed to find player {mc_username}")

            # get user avatar for minecraft uuid
            mc_uuid = data["data"]["player"]["id"]
            mc_raw_id = data["data"]["player"]["raw_id"]

            # ask user if the avatar looks correct
            # https://crafthead.net/armor/body/{uuid}
            avatar_url = f"https://crafthead.net/armor/body/{mc_raw_id}"
            fields = []
            for n in data["data"]["player"]["name_history"]:
                fields.append({"name": "Name", "value": n["name"]})

            response = await self.discord_helper.ask_yes_no(
                _ctx,
                _ctx.channel,
                "Verify Account",
                f"Is this your avatar associated with the Minecraft account {mc_username}?",
                fields=fields,
                image=avatar_url,
            )
            if not response:
                # if not, tell them to try again
                await self.discord_helper.sendEmbed(
                    _ctx.channel,
                    "Unable to Verify Account",
                    "Please run the command again to verify your account.",
                    color=0xFF0000,
                    delete_after=20,
                )
                return

            # if correct, add to whitelist
            # check if user is in the whitelist
            # minecraft_user = self.db.get_minecraft_user(ctx.author.id)
            self.db.whitelist_minecraft_user(ctx.author.id, mc_username, mc_uuid, True)
            await self.discord_helper.sendEmbed(
                _ctx.channel,
                "Whitelisted",
                f"You have been whitelisted for Minecraft account {mc_username}({mc_uuid}). It may take up to 15 minutes for the whitelist to reload.\n\nSee the #minecraft channel for required version and server address.\n\nIf you need help, message DarthMinos.",
                color=0x00FF00,
                delete_after=30,
            )

        except Exception as e:
            self.log.error(guild_id, "minecraft.whitelist", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    def is_user_whitelisted(self, user_id: int):
        # check if user is in the whitelist
        minecraft_user = self.db.get_minecraft_user(user_id)
        if not minecraft_user:
            return False

        # check if user is whitelisted
        if not minecraft_user["whitelist"]:
            return False

        return True

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No minecraft settings found for guild {guildId}")
        return cog_settings
def setup(bot):
    bot.add_cog(Minecraft(bot))
