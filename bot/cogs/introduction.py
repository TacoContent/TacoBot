import inspect
import os
import traceback

import discord
from bot.lib import discordhelper, logger, settings
from bot.lib.enums import loglevel, tacotypes
from bot.lib.messaging import Messaging
from bot.lib.mongodb.introductions import IntroductionsDatabase
from bot.lib.mongodb.settings import SettingsDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from discord.ext import commands


class IntroductionCog(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.SETTINGS_SECTION = "introduction"
        self.settings_db = SettingsDatabase()
        self.introductions_db = IntroductionsDatabase()
        self.tracking_db = TrackingDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.group(name="introduction", aliases=["intro"], invoke_without_command=True)
    async def introduction(self, ctx) -> None:
        pass

    @introduction.command(name="import", aliases=["i"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def introduction_import(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id

        try:
            await ctx.message.delete()

            cog_settings = self.get_cog_settings(guild_id)

            was_imported = cog_settings.get("was_imported", False)
            if was_imported:
                raise Exception("This guild has already been imported")

            channels = cog_settings.get("channels", [])
            approval_emoji = cog_settings.get("approval_emoji", ['🌟', '⭐'])

            tracked_users = []
            # get all the users that already have tracked introductions
            existing_introductions = [int(u['user_id']) for u in self.introductions_db.get_user_introductions(guild_id)]

            for channel_id in channels:
                channel = await self.discord_helper.get_or_fetch_channel(channelId=int(channel_id))
                if not channel or not isinstance(channel, discord.TextChannel):
                    raise Exception(f"Channel {channel_id} not found when trying to import")

                messages = channel.history(limit=200, oldest_first=True)
                async for message in messages:
                    if (
                        message.author.bot
                        or message.author.system
                        or message.author.id in tracked_users
                        or message.author.id in existing_introductions
                    ):
                        continue

                    if isinstance(message.author, discord.User):
                        # this means the user is no longer in the guild
                        continue

                    if message.type != discord.MessageType.default:
                        # we dont care about any other message type
                        continue

                    # check if the message has any of the approval emojis
                    has_approval_emoji = False
                    for r in message.reactions:
                        if r.emoji in approval_emoji:
                            # was this reaction added by the author?
                            async for user in r.users():
                                if user.id == message.author.id:
                                    has_approval_emoji = True
                                    break

                    reason_msg = f"Imported introduction from {channel.name} by {message.author.name}"
                    self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", reason_msg)

                    await self.discord_helper.taco_give_user(
                        guildId=guild_id,
                        fromUser=self.bot.user,
                        toUser=message.author,
                        reason=reason_msg,
                        give_type=tacotypes.TacoTypes.POST_INTRODUCTION,
                        taco_amount=0,
                    )

                    if has_approval_emoji:
                        reason_msg = f"{message.author.name} approved introduction in {channel.name}"
                        self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", reason_msg)
                        await self.discord_helper.taco_give_user(
                            guildId=guild_id,
                            fromUser=self.bot.user,
                            toUser=message.author,
                            reason=reason_msg,
                            give_type=tacotypes.TacoTypes.APPROVE_INTRODUCTION,
                            taco_amount=0,
                        )

                    # add the user to the tracked users list
                    tracked_users.append(message.author.id)
                    self.tracking_db.track_user_introduction(
                        guild_id=guild_id,
                        user_id=message.author.id,
                        channel_id=channel.id,
                        message_id=message.id,
                        approved=has_approval_emoji,
                    )

            # set the was_imported flag to true
            self.settings_db.set_setting(guildId=guild_id, name=self.SETTINGS_SECTION, key="was_imported", value=True)

            await self.messaging.send_embed(
                channel=ctx.channel,
                title="Import Complete",
                message=f"Successfully imported {len(tracked_users)} introductions from {len(channels)} channels",
                color=discord.Color.green().value,
                delete_after=10,
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, message: discord.Message) -> None:
        _method = inspect.stack()[0][3]
        if not message.guild:
            return

        guild_id = message.guild.id
        try:
            if message.author.bot or message.author.system:
                return

            # ignore messages that are commands
            for prefix in await self.bot.command_prefix(message):
                if message.content.startswith(prefix):
                    return

            cog_settings = self.get_cog_settings(guild_id)
            channels = cog_settings.get("channels", [])

            if not channels or str(message.channel.id) not in channels:
                return

            if message.type != discord.MessageType.default:
                # we dont care about any other message type
                return

            # is this user already tracked?
            tracked_user = self.introductions_db.get_user_introduction(guild_id, message.author.id)
            if tracked_user:
                return

            # # check if the message has any of the approval emojis
            # # will have to check this on the "on_raw_reaction_add" event as well
            # has_approval_emoji = False
            # for r in message.reactions:
            #     if r.emoji in approval_emoji:
            #         # was this reaction added by the author?
            #         async for user in r.users():
            #             if user.id == message.author.id:
            #                 has_approval_emoji = True
            #                 break

            reason_msg = self.settings.get_string(guild_id, "posting_introduction_reason")
            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=message.author,
                reason=reason_msg,
                give_type=tacotypes.TacoTypes.POST_INTRODUCTION,
                taco_amount=0,
            )

            self.tracking_db.track_user_introduction(
                guild_id=guild_id,
                user_id=message.author.id,
                channel_id=message.channel.id,
                message_id=message.id,
                approved=False,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=message.channel.id if message.channel else None,
                userId=message.author.id,
                command="introduction",
                subcommand="track",
                args=[{"type": "event"}, {"event": "on_message"}, {"message_id": str(message.id)}],
            )

            pass
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_raw_reaction_add(self, payload) -> None:
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id or 0
        try:
            if guild_id == 0:
                return
            if payload.event_type != 'REACTION_ADD':
                return

            if payload.member.bot or payload.member.system:
                return

            cog_settings = self.get_cog_settings(guild_id)
            approval_emoji = cog_settings.get("approval_emoji", ['🌟', '⭐'])
            channels = cog_settings.get("channels", [])
            if not channels or str(payload.channel_id) not in channels:
                return

            # get the channel
            channel = await self.discord_helper.get_or_fetch_channel(payload.channel_id)
            if not channel:
                return
            # get the original message
            message = await channel.fetch_message(payload.message_id)
            if not message:
                return
            author = message.author
            # was this added by the author?
            if payload.user_id != author.id:
                return

            # is the added emoji an approval emoji?
            if payload.emoji.name not in approval_emoji:
                return

            tracked_user = self.introductions_db.get_user_introduction(guild_id, message.author.id)
            if tracked_user and tracked_user.get('approved', False):
                return

            reason_msg = self.settings.get_string(guild_id, "approve_introduction_reason")
            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=message.author,
                reason=reason_msg,
                give_type=tacotypes.TacoTypes.APPROVE_INTRODUCTION,
                taco_amount=0,
            )

            self.tracking_db.track_user_introduction(
                guild_id=guild_id,
                user_id=message.author.id,
                channel_id=message.channel.id,
                message_id=message.id,
                approved=True,
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    def get_cog_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section="tacos")


async def setup(bot):
    await bot.add_cog(IntroductionCog(bot))
