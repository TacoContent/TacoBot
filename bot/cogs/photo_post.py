import os
import inspect
import re
import traceback

from discord.ext import commands
from .lib import settings, discordhelper, logger, loglevel, mongo, tacotypes


class PhotoPost(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "photo_post"
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if message.guild is not None:
                guild_id = message.guild.id
            if guild_id == 0:
                return
            # if the message is from a bot, ignore
            if message.author.bot:
                return

            # check if message has a link to the image in it
            media_regex = r"(https:\/\/)((?:cdn|media)\.discordapp\.(?:net|com))\/attachments\/\d+\/\d+\/\w+\.(png|jpe?g|gif|webp)"

            # get the settings from settings
            cog_settings = self.get_cog_settings(guild_id)

            allowed_channel_list = [
                c for c in cog_settings.get("channels", []) if str(c["id"]) == str(message.channel.id)
            ]
            post_channel = None
            if allowed_channel_list:
                post_channel = allowed_channel_list[0]

            if not post_channel:
                return

            # if the message is not a photo, ignore
            matches = re.search(media_regex, message.content, re.MULTILINE | re.DOTALL | re.UNICODE | re.IGNORECASE)
            if not message.attachments and matches is None:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Message {message.id} does not contain a photo",
                )
                return

            # # check if the user posted a photo in the channel within the last 5 minutes
            # # if so, ignore
            # now = datetime.datetime.utcnow()
            # five_minutes_ago = now - datetime.timedelta(minutes=5)
            # async for m in message.channel.history(limit=100, after=five_minutes_ago):
            #     if m.author == message.author and m.attachments:
            #         # check if the bot has already added reactions to the message
            #         # if so, ignore
            #         for r in post_channel['reactions']:
            #             if r in [r.emoji for r in m.reactions]:
            #                 self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}"", f"User {message.author} already posted a photo in the last 5 minutes")
            #                 self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Bot already reacted to message {m.id}")
            #                 return

            # this SHOULD get the amount from the `tacos` settings, but it doesn't
            amount = int(post_channel["tacos"] if "tacos" in post_channel else 5)
            amount = amount if amount > 0 else 5

            reason_msg = f"Photo post in #{message.channel.name}"

            for r in post_channel["reactions"]:
                await message.add_reaction(r)

            # if the message is a photo, add tacos to the user
            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=message.author,
                reason=reason_msg,
                give_type=tacotypes.TacoTypes.PHOTO_POST,
                taco_amount=amount,
            )

            # track the message in the database
            image_url = message.attachments[0].url if message.attachments else matches.group(0) if matches else None
            self.db.track_photo_post(
                guildId=guild_id,
                userId=message.author.id,
                messageId=message.id,
                channelId=message.channel.id,
                message=message.content,
                image=image_url,
                channelName=message.channel.name,
            )

            pass
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            traceback.print_exc()

    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings

    
async def setup(bot):
    await bot.add_cog(PhotoPost(bot))
