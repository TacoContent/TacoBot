import inspect
import json
import math
import os
import traceback
import uuid
from random import random
from urllib import parse, request

from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.tacobot import TacoBot
from discord.ext import commands


class Giphy(TacobotCog):
    def __init__(self, bot: TacoBot):
        super().__init__(bot, "giphy")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.command(name='giphy', aliases=['gif'])
    @commands.guild_only()
    async def giphy(self, ctx, *, query: str = "tacos"):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
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
                'rating': 'r',
            }
            url = url + '?' + parse.urlencode(params)
            with request.urlopen(url) as f:
                data = json.loads(f.read().decode())
            if 'data' in data and len(data['data']) > 0:
                random_index = math.floor(random() * len(data['data']))
                title = data['data'][random_index]['title']
                image_url = data['data'][random_index]['images']['original']['url']
                url = data['data'][random_index]['url']

                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=title,
                    image=image_url,
                    url=url,
                    color=0x00FF00,
                    author=ctx.author,
                    footer="Powered by Giphy",
                )
                # embed = discord.Embed(title=data['data'][random_index]['title'], url=data['data'][random_index]['url'], color=0x00ff00)
                # embed.set_image(url=data['data'][random_index]['images']['original']['url'])
                # await ctx.send(embed=embed)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="giphy",
                subcommand=None,
                args=[{"type": "command"}, {"query": query}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)


async def setup(bot):
    await bot.add_cog(Giphy(bot))
