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

from . import utils
from . import logger
from . import loglevel
from . import settings

import inspect

class DiscordHelper():
    def __init__(self, bot):
        self.settings = settings.Settings()
        self.bot = bot
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        pass

    async def sendEmbed(self, channel, title, message, fields=None, delete_after=None, footer=None, components=None):
        embed = discord.Embed(title=title, description=message, color=0x7289da)
        if fields is not None:
            for f in fields:
                embed.add_field(name=f['name'], value=f['value'], inline='false')
        if footer is None:
            embed.set_footer(text=f'Developed by {self.settings.author}')
        else:
            embed.set_footer(text=footer)
        return await channel.send(embed=embed, delete_after=delete_after, components=components)

    async def notify_of_error(self, ctx):
        await self.sendEmbed(ctx.channel, "Error", f'{ctx.author.mention}, There was an error trying to complete your request. The error has been logged. I am very sorry.', delete_after=30)

    async def get_or_fetch_user(self, userId: int):
        _method = inspect.stack()[1][3]
        try:
            if userId:
                user = self.bot.get_user(userId)
                if not user:
                    user = await self.bot.fetch_user(userId)
                return user
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_channel(self, channelId: int):
        _method = inspect.stack()[1][3]
        try:
            if channelId:
                chan = self.bot.get_channel(channelId)
                if not chan:
                    chan = await self.bot.fetch_channel(channelId)
                return chan
            else:
                return  None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    def get_by_name_or_id(self, iterable, nameOrId: typing.Union[int, str]):
        if isinstance(nameOrId, str):
            return discord.utils.get(iterable, name=str(nameOrId))
        elif isinstance(nameOrId, int):
            return discord.utils.get(iterable, id=int(nameOrId))
        else:
            return None

    async def ask_yes_no(self, ctx, question: str, title: str = "Voice Channel Setup"):
        guild_id = ctx.guild.id
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        buttons = [
            create_button(style=ButtonStyle.green, label=self.get_string(guild_id, 'yes'), custom_id="YES"),
            create_button(style=ButtonStyle.red, label=self.get_string(guild_id, 'no'), custom_id="NO")
        ]
        yes_no = False
        action_row = create_actionrow(*buttons)
        yes_no_req = await self.sendEmbed(ctx.channel, title, question, components=[action_row], delete_after=60, footer=self.get_string(guild_id, 'footer_60_seconds'))
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.get_string(guild_id, 'took_too_long'), delete_after=5)
        else:
            yes_no = utils.str2bool(button_ctx.custom_id)
            await yes_no_req.delete()
        return yes_no
