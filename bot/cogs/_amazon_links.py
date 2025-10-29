# Before: https://www.amazon.com/dp/B0042TVKZY/
# After: https://www.amazon.com/dp/B0042TVKZY/?tag=darthminos0f-20
import inspect
import os
import re
import traceback

from discord.ext import commands

from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.messaging import Messaging
from bot.tacobot import TacoBot


class AmazonLinkCog(TacobotCog):
    def __init__(self, bot: TacoBot):
        super().__init__(bot, "amazon_links")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.affiliate_tag = "darthminos0f-20"

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

            pattern = re.compile(r"<?(https://(?:(?:www|smile)\.)?amazon\.com/(.*)?)>?", flags=re.IGNORECASE)
            match = pattern.search(message.content)
            if not match:
                return

            # get the content of the message and replace the amazon link with the affiliate link
            message_content = message.content
            # remove existing affiliate tag
            message_content = re.sub(r"\?tag=[a-zA-Z0-9\-_]+", "", message_content)
            match = pattern.search(message_content)
            if not match:
                return

            # extract the full amazon link
            amazon_link = match.group(1)
            # remove the original link from the message completely
            message_content = message_content.replace(amazon_link, "")
            # if link has a ? in it, add the affiliate tag with an &
            if "?" in amazon_link:
                amazon_link = f"{amazon_link}&tag={self.affiliate_tag}"
            else:
                amazon_link = f"{amazon_link}?tag={self.affiliate_tag}"

            await message.delete()

            # create an embed with the original message and the new url
            await self.messaging.send_embed(
                channel=message.channel,
                title="Amazon Link",
                message=f"{message_content}",
                author=message.author,
                content=f"Please consider using this link which can help support the discord.\n\n{amazon_link}",
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())


def setup(bot):
    bot.add_cog(AmazonLinkCog(bot))
