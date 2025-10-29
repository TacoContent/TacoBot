# Before: https://twitter.com/MarkH90441396/status/1734689257946591509
# After: https://vxtwitter.com/MarkH90441396/status/1734689257946591509
import inspect
import os
import re
import traceback

from discord.ext import commands

from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.messaging import Messaging
from bot.tacobot import TacoBot


class TwitterPreviewCog(TacobotCog):
    def __init__(self, bot: TacoBot):
        super().__init__(bot, "twitter_preview")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)

        self.log.debug(0, f"{self._module}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message):
        guild_id = 0
        _method = inspect.stack()[0][3]
        try:
            # if in a DM, ignore
            if message.guild is None:
                return
            # if the message is from a bot, ignore
            if message.author.bot or message.author.system:
                return
            guild_id = message.guild.id

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings["enabled"]:
                return

            # check if message is a command
            # get the command prefix
            command_prefix = await self.bot.get_prefix(message)
            for prefix in command_prefix:
                if message.content.startswith(prefix):
                    return

            pattern = re.compile(r"(https://(?:(?:www)\.)?(twitter|x)\.com/(.*)?/status/(.*)?)", flags=re.IGNORECASE)
            match = pattern.search(message.content)
            if not match:
                return

            # extract the full twitter link
            twitter_link = match.group(1)
            domain = match.group(2)

            # if the link is already a vxtwitter link, ignore
            if twitter_link.startswith("https://vxtwitter.com"):
                return

            # replace the twitter link with the vxtwitter link
            twitter_link = twitter_link.replace(f"https://{domain}.com", "https://vxtwitter.com")

            # create an embed with the original message and the new url
            await message.channel.send(content=twitter_link)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())


async def setup(bot):
    await bot.add_cog(TwitterPreviewCog(bot))
