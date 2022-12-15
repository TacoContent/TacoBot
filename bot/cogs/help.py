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
import re

from discord.ext.commands.cooldowns import BucketType
from interactions import ComponentContext
# from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
# from discord_slash.model import ButtonStyle
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

    @commands.command(name='changelog', aliases=['changes', "cl"])
    async def changelog(self, ctx):
        _method = inspect.stack()[0][3]
        try:
            await ctx.message.delete()
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            with open(self.settings.changelog, 'r', encoding="UTF-8") as f:
                changelog_data = f.read().strip()

            # split changelog into sections based on '**\d{1,}\.\d{1,}\.\d{1,}**'
            sections = re.split(r'(\*\*v?\d{1,}\.\d{1,}\.\d{1,}\*\*)', changelog_data)
            versions = {}
            cversion = None
            for s in list(filter(lambda x: x != '' and x != None, sections)):
                if s == '' or s == None:
                    continue

                if s.startswith('**'):
                    cversion = s.strip()
                    versions[cversion] = ''
                else:
                    if cversion and cversion in versions:
                        versions[cversion] += s
            # chunk in to 25 sections
            chunked = utils.chunk_list(list(versions.keys()), 25)
            pages = math.ceil(len(list(versions.keys())) / 25)
            page = 1
            for chunk in chunked:
                fields = list()
                for v in chunk:
                    # get the version from the section
                    if v and v in versions:
                        section = versions[v]
                        s = section
                        if s:
                            # if section is longer than 1024 characters, truncate and add '…'
                            if len(section) > 1024:
                                s = section[:1023] + '…'
                            fields.append({"name": v, "value": s, "inline": False})
                if len(fields) > 0:
                    await self.discord_helper.sendEmbed(ctx.channel,
                    self.settings.get_string(guild_id, "help_changelog_title", bot_name=self.settings.name, page=page, total_pages=pages),
                    "", footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version), fields=fields)
                page += 1
        except Exception as ex:
            self.log.error(ctx.guild.id, _method, str(ex), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)



    @commands.group(name="help", aliases=["h"], invoke_without_command=True)
    async def help(self, ctx, command: str = None, subcommand: str = None):
        _method = inspect.stack()[1][3]
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0
        if guild_id != 0:
            await ctx.message.delete()
        if command is None:
            await self.root_help(ctx)
        else:
            await self.subcommand_help(ctx, command, subcommand)

    async def subcommand_help(self, ctx, command: str = None, subcommand: str = None):
        _method = inspect.stack()[1][3]
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0

        try:
            command = command.lower() if command else None
            subcommand = subcommand.lower() if subcommand else None

            command_list = self.settings.commands
            if command not in command_list.keys():
                await self.discord_helper.sendEmbed(ctx.channel,
                    self.settings.get_string(guild_id, "help_title", bot_name=self.settings.name),
                    self.settings.get_string(guild_id, "help_no_command", command=command),
                    color=0xFF0000, delete_after=20)
                return

            cmd = command_list[command]

            fields = list()
            is_admin = False
            if 'admin' in cmd:
                is_admin = cmd['admin']
            shield = '🛡️' if is_admin else ''
            fields.append({"name": f"{shield}{cmd['title']}", "value": cmd['description']})
            fields.append({"name": 'help', "value": f"`{self._prefix(cmd['usage'])}`"})
            fields.append({"name": 'more', "value": self.prefix(f'`{{{{prefix}}}} help {command.lower()}`')})
            if 'examples' in cmd:
                example_list = [ f"`{self._prefix(e)}`" for e in cmd['examples'] ]
                if example_list and len(example_list) > 0:
                    examples = '\n'.join(example_list)
                    fields.append({"name": 'examples', "value": examples})
            await self.discord_helper.sendEmbed(ctx.channel,
                self.settings.get_string(guild_id, "help_command_title", bot_name=self.settings.name, command=command), "",
                footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version), fields=fields)


            subcommands = cmd["subcommands"]
            if subcommand is None:
                filtered_list = subcommands.keys()
            else:
                filtered_list = [i for i in subcommands.keys() if i.lower() == subcommand]

            chunked = utils.chunk_list(list(filtered_list), 10)
            pages = math.ceil(len(filtered_list) / 10)
            page = 1
            for chunk in chunked:
                fields = list()
                for k in chunk:
                    scmd = subcommands[k.lower()]
                    is_admin = False
                    if 'admin' in scmd:
                        is_admin = scmd['admin']
                    shield = '🛡️' if is_admin else ''
                    fields.append({"name": f"{shield}{scmd['title']}", "value": scmd['description']})
                    fields.append({"name": 'help', "value": f"`{self.prefix(scmd['usage'])}`"})
                    fields.append({"name": 'more', "value": self.prefix(f'`{{{{prefix}}}} help {command.lower()} {k.lower()}`')})
                    if 'examples' in scmd:
                        example_list = [ f"`{self._prefix(e)}`" for e in scmd['examples'] ]
                        if example_list and len(example_list) > 0:
                            examples = '\n'.join(example_list)
                            fields.append({"name": 'examples', "value": examples})

                await self.discord_helper.sendEmbed(ctx.channel,
                    self.settings.get_string(guild_id, "help_group_title", bot_name=self.settings.name, page=page, total_pages=pages), "",
                    footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version), fields=fields)
                page += 1


        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    async def root_help(self, ctx):
        _method = inspect.stack()[1][3]
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0

        try:
            command_list = self.settings.commands
            filtered_list = list()
            filtered_list = [i for i in command_list.keys()]

            chunked = utils.chunk_list(list(filtered_list), 10)
            pages = math.ceil(len(filtered_list) / 10)
            page = 1
            for chunk in chunked:
                fields = list()
                for k in chunk:
                    cmd = command_list[k.lower()]
                    is_admin = False
                    if 'admin' in cmd:
                        is_admin = cmd['admin']
                    shield = '🛡️' if is_admin else ''
                    fields.append({"name": f"{shield}{cmd['title']}", "value": cmd['description']})
                    fields.append({"name": 'help', "value": f"`{self._prefix(cmd['usage'])}`"})
                    fields.append({"name": 'more', "value": self.prefix(f'`{{{{prefix}}}} help {k.lower()}`')})
                    if 'examples' in cmd:
                        example_list = [ f"`{self._prefix(e)}`" for e in cmd['examples'] ]
                        if example_list and len(example_list) > 0:
                            examples = '\n'.join(example_list)
                            fields.append({"name": 'examples', "value": examples})
                await self.discord_helper.sendEmbed(ctx.channel, f"{self.settings.name} Help ({page}/{pages})", "",
                    footer=self.settings.get_string(guild_id, "version_footer", version=self.settings.version), fields=fields)
                page += 1
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    def clean_command_name(self, command):
        return command.replace("_", " ").lower()

    def _prefix(self, s):
        return utils.str_replace(s, prefix=self.settings.get("prefixes", [".taco "]))

    @help.command(name="")
    async def help_command(self, ctx):
        pass

async def setup(bot):
    await bot.add_cog(Help(bot))
