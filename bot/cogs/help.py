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

from discord.ext.commands.cooldowns import BucketType
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure
import inspect

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider


class Help(commands.Cog):
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
        self.log.debug(0, "help.__init__", "Initialized")



    @commands.group(name="help", aliases=["h"], invoke_without_command=True)
    async def help(self, ctx):
        pass

    @help.command(name="")
    async def help_command(self, ctx):
        _method = inspect.stack()[1][3]
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0

        try:
            command_list = self.settings.commands
            filtered_list = list()
            # if self.isAdmin(ctx):
            filtered_list = [i for i in command_list.keys()]
            # else:
            #     filtered_list = [i for i in command_list.keys() if command_list[i]['admin'] == False]

            chunked = utils.chunk_list(list(filtered_list), 10)
            pages = math.ceil(len(filtered_list) / 10)
            page = 1
            for chunk in chunked:
                fields = list()
                for k in chunk:
                    cmd = command_list[k.lower()]
                    if cmd['admin'] and self.isAdmin(ctx):
                        fields.append({"name": cmd['title'], "value": cmd['message']})
                        fields.append({"name": 'help', "value": f"`{cmd['usage']}`"})
                        fields.append({"name": 'more', "value": f"`.taco {k.lower()} help`"})
                    else:
                        fields.append({"name": cmd['title'], "value": cmd['message']})
                        fields.append({"name": 'help', "value": f"`{cmd['usage']}`"})
                        fields.append({"name": 'more', "value": f"`.taco {k.lower()} help`"})

                await self.sendEmbed(ctx.channel, f"{self.settings.name} Help ({page}/{pages})", f"Version {self.settings.version}", fields=fields)
                page += 1
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.notify_of_error(ctx)
        if guild_id != 0:
            await ctx.message.delete()

def setup(bot):
    bot.add_cog(Help(bot))
