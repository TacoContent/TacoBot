# this watches channels, and requires a user to have tacos to post in the channel
import inspect
import os
import traceback

from bot.lib import discordhelper, logger, settings
from bot.lib.enums import loglevel
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tacos import TacosDatabase
from discord.ext import commands


class TacoPost(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        # pull from database instead of app.manifest
        self.SETTINGS_SECTION = 'tacopost'

        self.tacos_db = TacosDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        _method = inspect.stack()[0][3]
        # if in a DM, ignore
        if message.guild is None:
            return

        guild_id = message.guild.id
        user = message.author
        channel = message.channel
        try:
            if message.author.bot:
                return

            # get the settings for tacopost out of the settings
            tacopost_settings = self.settings.get_settings(guild_id, self.SETTINGS_SECTION)
            if not tacopost_settings:
                # raise exception if there are no suggestion settings
                self.log.error(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No tacopost settings found for guild {guild_id}",
                )
                await self.discord_helper.notify_bot_not_initialized(message, "tacopost")
                return

            # get the channels for tacopost out of the settings
            tacopost_channels = tacopost_settings.get('channels', [])
            # if channel.id is not in CHANNELS[].id return
            if str(channel.id) not in [c['id'] for c in tacopost_channels]:
                return

            channel_settings = [c for c in tacopost_channels if c['id'] == str(channel.id)][0]
            if channel_settings is None:
                return

            # check if the user is in the role set in channel_settings['exempt'][]
            exempt_list = channel_settings.get('exempt', [])
            if str(user.id) in exempt_list:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"User {user.name} is exempt from having to pay tacos in channel {channel.name}",
                )
                return
            for role in user.roles:
                if str(role.id) in exempt_list:
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"User {user.name} is exempt from having to pay tacos in channel {channel.name}",
                    )
                    return

            prefix = await self.bot.get_prefix(message)
            # if the message starts with one of the items in the array self.bot.command_prefix, exit the function
            if any(message.content.startswith(p) for p in prefix):
                return

            # get required tacos cost for channel in CHANNELS[]
            taco_cost = [c for c in tacopost_channels if c['id'] == str(channel.id)][0]['cost']
            # get tacos count for user
            taco_count = self.tacos_db.get_tacos_count(guild_id, user.id)
            # if user has doesnt have enough tacos, send a message, and delete their message
            if taco_count is None or taco_count < taco_cost:
                await self.messaging.send_embed(
                    channel=channel,
                    title="Not Enough Tacos",
                    message=f"{user.mention}, You need {taco_cost} tacos to post in this channel.",
                    delete_after=15,
                )
                await message.delete()
            else:

                async def response_callback(response):
                    if response:
                        # remove the tacos from the user
                        self.tacos_db.remove_tacos(guild_id, user.id, taco_cost)
                        # send the message that tacos have been removed
                        await self.messaging.send_embed(
                            channel=channel,
                            title="Tacos Removed",
                            message=f"{user.mention}, You have been charged {taco_cost} tacos from your account.",
                            delete_after=10,
                        )
                    else:
                        await self.messaging.send_embed(
                            channel=channel,
                            title="Message Removed",
                            message=f"{user.mention}, You chose to not use your tacos, your message has been removed.",
                            delete_after=10,
                        )
                        await message.delete()

                await self.discord_helper.ask_yes_no(
                    ctx=message,
                    targetChannel=message.channel,
                    question=f"{user.mention}, Are you sure you want to post in this channel?\n\n**It will cost you {taco_cost} tacos 🌮.**\n\nYou currently have {taco_count} tacos 🌮.",
                    title="Use tacos to post?",
                    result_callback=response_callback,
                )
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())


async def setup(bot):
    await bot.add_cog(TacoPost(bot))
