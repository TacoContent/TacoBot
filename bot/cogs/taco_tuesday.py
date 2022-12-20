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
        self.SETTINGS_SECTION = "tacos"
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
    async def give(self, ctx: Context, member: discord.Member):
        guild_id = ctx.guild.id
        try:

            await ctx.message.delete()
            taco_settings = self.get_tacos_settings(guildId = guild_id)
            if not taco_settings:
                # raise exception if there are no tacos settings
                self.log.error(guild_id, "tacos.on_raw_reaction_add", f"No tacos settings found for guild {guild_id}")
                return

            amount = taco_settings.get("taco_tuesday_count", 250)
            reason = taco_settings.get("taco_tuesday_reason", "Taco Tuesday Tacos")

            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reason_msg = self.settings.get_string(guild_id, "taco_reason_default")
            if reason:
                reason_msg = f"{reason}"

            await self.discord_helper.sendEmbed(ctx.channel,
                self.settings.get_string(guild_id, "taco_give_title"),
                # 	"taco_gift_success": "{{user}}, You gave {touser} {amount} {taco_word} 🌮.\n\n{{reason}}",
                self.settings.get_string(guild_id, "taco_gift_success", user=self.bot.user, touser=member.mention, amount=amount, taco_word=tacos_word, reason=reason_msg),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT)

            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=member,
                reason=reason_msg,
                give_type=tacotypes.TacoTypes.CUSTOM,
                taco_amount=amount
            )

        except Exception as e:
            self.log.error(ctx.guild.id, "taco_tuesday.give", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    def get_tacos_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings
async def setup(bot):
    await bot.add_cog(TacoTuesday(bot))
