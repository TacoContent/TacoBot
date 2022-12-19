import json
from random import random
from urllib import parse, request
import discord
from discord.ext import commands
import asyncio
import traceback
import sys
import os
import glob
import typing
import math
import re
import uuid

from discord.ext.commands.cooldowns import BucketType
from interactions import ComponentContext
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

class Giphy(commands.Cog):
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
        self.log.debug(0, "giphy.__init__", "Initialized")

    @commands.command(name='giphy', aliases=['gif'])
    async def giphy(self, ctx, *, query: str = "tacos"):
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id
                await ctx.message.delete()

            url = 'http://api.giphy.com/v1/gifs/search'
            params = {
                'q': query,
                'api_key': self.settings.giphy_api_key,
                'limit': 50,
                'offset': math.floor(random() * 50),
                "random_id": uuid.uuid4().hex,
                'rating': 'r'
            }
            url = url + '?' + parse.urlencode(params)
            with request.urlopen(url) as f:
                data = json.loads(f.read().decode())
            if 'data' in data and len(data['data']) > 0:
                random_index = math.floor(random() * len(data['data']))
                title = data['data'][random_index]['title']
                image_url = data['data'][random_index]['images']['original']['url']
                url = data['data'][random_index]['url']

                await self.discord_helper.sendEmbed(
                    channel=ctx.channel,
                    title=title,
                    image=image_url,
                    url=url,
                    color=0x00ff00,
                    author=ctx.author,
                    footer="Powered by Giphy")
                # embed = discord.Embed(title=data['data'][random_index]['title'], url=data['data'][random_index]['url'], color=0x00ff00)
                # embed.set_image(url=data['data'][random_index]['images']['original']['url'])
                # await ctx.send(embed=embed)
        except Exception as e:
            self.log.error(guild_id, "giphy.giphy", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

async def setup(bot):
    await bot.add_cog(Giphy(bot))
