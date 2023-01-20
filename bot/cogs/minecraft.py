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

    @commands.group(name="minecraft", invoke_without_command=True)
    async def minecraft(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        guild_id = 0
        try:
            pass
        except Exception as e:
            self.log.error(guild_id, "minecraft.minecraft", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @minecraft.command()
    @commands.guild_only()
    async def whitelist(self, ctx: Context):
        guild_id = 0
        try:
            if ctx.guild:
                await ctx.message.delete()
                guild_id = ctx.guild.id

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
                return
            data = result.json()
            # get users uuid for minecraft username
            if not data["success"] or data["code"] != "player.found":
                self.log.warn(guild_id, "minecraft.whitelist", f"Failed to find player {mc_username}")

            # get user avatar for minecraft uuid
            mc_uuid = data["data"]["player"]["id"]

            # ask user if the avatar looks correct
            # https://crafthead.net/armor/body/{uuid}
            avatar_url = f"https://crafthead.net/armor/body/{mc_uuid}"
            fields = []
            for n in data["data"]["player"]["meta"]["name_history"]:
                fields.append({"name": "Name", "value": n["name"]})

            async def yes_no_callback(response: bool):
                if not response:
                    await self.discord_helper.sendEmbed(
                        _ctx.channel,
                        self.settings.get_string(guild_id, "minecraft_verification_failed_title"),
                        self.settings.get_string(guild_id, "minecraft_verification_failed_message"),
                        color=0xFF0000,
                        delete_after=20,
                    )
                else:
                    # if correct, add to whitelist
                    # check if user is in the whitelist
                    # minecraft_user = self.db.get_minecraft_user(ctx.author.id)
                    self.db.whitelist_minecraft_user(ctx.author.id, mc_username, mc_uuid, True)
                    await self.discord_helper.sendEmbed(
                        _ctx.channel,
                        self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                        self.settings.get_string(guild_id, "minecraft_whitelist_message", username=mc_username, uuid=mc_uuid, server="mc.fuku.io", modpack="All The Mods 7 v0.4.0"),
                        color=0x00FF00,
                        delete_after=30,
                    )

            await self.discord_helper.ask_yes_no(
                _ctx,
                _ctx.channel,
                self.settings.get_string(guild_id, "minecraft_ask_avatar_title"),
                self.settings.get_string(guild_id, "minecraft_ask_avatar_message", username=mc_username),
                fields=fields,
                image=avatar_url,
                result_callback=yes_no_callback,
            )


        except Exception as e:
            self.log.error(guild_id, "minecraft.whitelist", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            # raise Exception(f"No live_now settings found for guild {guildId}")
            return None
        return cog_settings

async def setup(bot):
    await bot.add_cog(Minecraft(bot))
