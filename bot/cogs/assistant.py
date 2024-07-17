import inspect
import json
import os
import traceback

import discord
from bot.lib import logger, settings
from bot.lib.enums import loglevel
from bot.lib.mongodb.tacos import TacosDatabase
from discord.ext import commands
from openai import OpenAI


class Assistant(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.tacos_db = TacosDatabase()
        self.settings = settings.Settings()
        self.SETTINGS_SECTION = "assistant"
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, message):
        _method = inspect.stack()[0][3]
        guild_id = 0
        if message.guild:
            guild_id = message.guild.id
        else:
            return

        if message.author == self.bot.user:
            return
        try:
            if not message.content.startswith(self.bot.user.mention):
                pass

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                return

            # tacos_settings = self.get_tacos_settings(guild_id)

            faq = await self._get_message_content_for_prompt(
                guildId=guild_id, channelId=int("948278701290840074"), messageId=int("1243617386981232670")
            )
            system = f"Your name is {self.bot.user.name}. You are in the {message.guild.name} discord. You are a discord assistant. You are here to help users with their questions. You can answer questions, provide information, and help users with their needs. You can also provide links to resources, and help users find the information they need. Your responses should be positive and fun."
            channels = json.dumps(await self._get_channels(guild_id))
            self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Channels: {channels}")
            user_prompt = message.content.replace(self.bot.user.mention, "").strip()
            user_json = self._get_user_json(guild_id, message.author)
            openai = OpenAI()
            airesponse = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"{system}\nFAQ: {faq}\nJSON of the Channels: {channels}\nAlways use the channels mention to link to the channel.",
                    },
                    {
                        "role": "user",
                        "content": f"{user_prompt}\nJSON of my user info:\n{user_json}\nUse my mention to ping me in your response.",
                    },
                ],
            )
            aiquestion = airesponse.choices[0].message.content
            await message.channel.send(aiquestion)
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{str(ex)}", traceback.format_exc())

    def _get_user_json(self, guildId: int, user: discord.Member) -> str:
        _method = inspect.stack()[0][3]
        try:
            # get_tacos_count(self, guildId: int, userId: int)
            taco_count = self.tacos_db.get_tacos_count(guildId=guildId, userId=user.id)
            return json.dumps({"name": user.mention, "id": user.id, "mention": user.mention, "taco_count": taco_count})
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(ex)}", traceback.format_exc())
            return ""

    async def _get_message_content_for_prompt(self, guildId: int, channelId: int, messageId: int) -> str:
        _method = inspect.stack()[0][3]
        try:
            guild = await self.bot.fetch_guild(guildId)
            channel = await guild.fetch_channel(channelId)
            message = await channel.fetch_message(messageId)
            return message.content
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(ex)}", traceback.format_exc())
            return ""

    async def _get_channels(self, guildId: int) -> list[dict]:
        _method = inspect.stack()[0][3]
        try:
            channels = []
            for g in [x for x in self.bot.guilds if x.id == guildId]:
                for c in [
                    x
                    for x in g.channels
                    if x.type == discord.ChannelType.text
                    or x.type == discord.ChannelType.news
                    or x.type == discord.ChannelType.forum
                    or x.type == discord.ChannelType.public_thread
                    or x.type == discord.ChannelType.private_thread
                    or x.type == discord.ChannelType.news_thread
                ]:
                    channels.append(
                        {
                            "id": c.id,
                            "name": f"#{c.name}",
                            "mention": c.mention,
                            "category": c.category.name if c.category else "",
                            "topic": c.topic if c.topic else "",
                            "created_at": c.created_at.isoformat(),
                        }
                    )
            return channels
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(ex)}", traceback.format_exc())
            return []

    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings


async def setup(bot):
    await bot.add_cog(Assistant(bot))
