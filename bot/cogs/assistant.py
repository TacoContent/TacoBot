import inspect
import json
import os
import traceback
import typing

import discord
from bot.lib import utils
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.helpers import EntityHelper
from bot.lib.mongodb.tacos import TacosDatabase
from bot.lib.openai import OpenAIHelper
from bot.tacobot import TacoBot
from discord.ext import commands
from lib.settings import Settings


class AssistantCog(TacobotCog):
    def __init__(self, bot: TacoBot, tacos_db: TacosDatabase, entity_helper: EntityHelper, settings: Settings):
        super().__init__(bot, "assistant", settings=settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.tacos_db = tacos_db
        self.entity_helper = entity_helper
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
            if not self.bot or not self.bot.user:
                return

            if not message.content.startswith(self.bot.user.mention):
                return

            ai_question = await self._ai_request(guild_id, message)
            if ai_question:
                await message.channel.send(ai_question)
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{str(ex)}", traceback.format_exc())

    async def _ai_request(self, guild_id: int, message: discord.Message) -> typing.Optional[str]:
        _method = inspect.stack()[0][3]

        if message.author == self.bot.user:
            return None
        if message.guild is None:
            return None
        if self.bot.user is None:
            return None

        cog_settings = self.get_cog_settings(guild_id)
        if not cog_settings.get("enabled", False):
            return None

        faq_settings = cog_settings.get("faq", {})

        faq_channel_id = faq_settings.get("channel_id", "948278701290840074")
        faq_message_id = faq_settings.get("message_id", "1243617386981232670")

        faq = await self._get_message_content_for_prompt(channel_id=int(faq_channel_id), message_id=int(faq_message_id))
        prompt = utils.str_replace(
            cog_settings.get("system_prompt", ""), bot_name=self.bot.user.name, guild_name=message.guild.name
        )

        # Get OpenAI settings from the 'openai' section
        openai_settings = self.get_settings(guild_id, "openai")

        # use the Model from the cog settings if specified
        if "model" in cog_settings:
            openai_settings["model"] = cog_settings["model"]

        # Initialize OpenAI helper with settings
        openai_helper = OpenAIHelper(settings=openai_settings)

        channels = json.dumps(await self._get_channels(guild_id))
        self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Channels: {channels}")
        user_prompt = message.content.replace(self.bot.user.mention, "").strip()
        user_json = self._get_user_json(guild_id, message.author)

        # Use the helper to make the chat completion request
        ai_response = openai_helper.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": f"{prompt}\nFAQ: {faq}\nJSON of the Channels: {channels}\nAlways use the channels mention to link to the channel.",
                },
                {
                    "role": "user",
                    "content": f"{user_prompt}\nJSON of my user info:\n{user_json}\nUse my mention to ping me in your response.",
                },
            ]
        )

        # Extract response text using the helper
        ai_question = openai_helper.get_response_text(ai_response)
        return ai_question

    def _get_user_json(self, guildId: int, user: typing.Union[discord.Member, discord.User]) -> str:
        _method = inspect.stack()[0][3]
        try:
            # get_tacos_count(self, guildId: int, userId: int)
            taco_count = self.tacos_db.get_tacos_count(guildId=guildId, userId=user.id)
            return json.dumps({"name": user.mention, "id": user.id, "mention": user.mention, "taco_count": taco_count})
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(ex)}", traceback.format_exc())
            return ""

    async def _get_message_content_for_prompt(self, channel_id: int, message_id: int) -> str:
        _method = inspect.stack()[0][3]
        try:
            channel = await self.entity_helper.get_or_fetch_channel(channel_id)
            if not channel:
                return ""
            message = await channel.fetch_message(message_id)
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


async def setup(bot):
    settings = Settings()
    tacos_db = TacosDatabase()
    entity_helper = EntityHelper(bot)

    await bot.add_cog(AssistantCog(bot=bot, tacos_db=tacos_db, entity_helper=entity_helper, settings=settings))
