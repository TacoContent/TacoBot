import inspect
import os
import traceback
import typing

import discord
from bot.cogs.lib import discordhelper, logger, settings
from bot.cogs.lib.enums import loglevel, tacotypes
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.mongodb.tacos import TacosDatabase
from bot.cogs.lib.mongodb.tracking import TrackingDatabase
from discord.ext import commands


class Tacos(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.SETTINGS_SECTION = "tacos"
        self.SELF_DESTRUCT_TIMEOUT = 30

        self.tacos_db = TacosDatabase()
        self.tracking_db = TrackingDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    # @app_commands.command(name="tacos", description="Taco related commands")
    # @app_commands.guild_only()
    # async def ac_tacos(self, interaction: discord.Interaction) -> None:
    #     _method = inspect.stack()[0][3]
    #     guild_id = interaction.guild.id if interaction.guild else 0

    #     try:
    #         pass
    #     except Exception as e:
    #         self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"Exception: {e}", traceback.format_exc())

    # @app_commands.command(name="count", description="Help for the tacos module")
    # @app_commands
    # @app_commands.guild_only()
    # async def ac_tacos_count(self, interaction: discord.Interaction) -> None:
    #     pass

    @commands.group()
    async def tacos(self, ctx) -> None:
        pass

    # create command called remove_all_tacos that asks for the user
    @tacos.command(aliases=['purge'])
    @commands.has_permissions(administrator=True)
    async def remove_all_tacos(self, ctx, user: discord.Member, *, reason: typing.Union[str, None] = None) -> None:
        _method = inspect.stack()[0][3]
        try:
            guild_id = ctx.guild.id
            await ctx.message.delete()
            self.tacos_db.remove_all_tacos(guild_id, user.id)
            reason_msg = reason if reason else "No reason given."
            await self.messaging.send_embed(
                channel=ctx.channel,
                title="Removed All Tacos",
                message=f"{user.mention} has lost all their tacos.",
                delete_after=self.SELF_DESTRUCT_TIMEOUT,
            )
            await self.discord_helper.taco_purge_log(ctx.guild.id, user, ctx.author, reason_msg)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel.id else None,
                userId=ctx.author.id,
                command="tacos",
                subcommand="purge",
                args=[{"type": "command"}, {"user_id": user.id}, {"reason": reason_msg}],
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)
            await ctx.message.delete()

    @tacos.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def give(self, ctx, member: discord.Member, amount: int, *, reason: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()
            # if the user that ran the command is the same as member, then exit the function
            if ctx.author.id == member.id:
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(guild_id, "error"),
                    message=self.settings.get_string(guild_id, "taco_self_gift_message", user=ctx.author.mention),
                    footer=self.settings.get_string(
                        guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT
                    ),
                    delete_after=self.SELF_DESTRUCT_TIMEOUT,
                )
                return

            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reason_msg = self.settings.get_string(guild_id, "taco_reason_default")
            if reason:
                reason_msg = f"{reason}"

            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "taco_give_title"),
                # 	"taco_gift_success": "{{user}}, You gave {touser} {amount} {taco_word} 🌮.\n\n{{reason}}",
                message=self.settings.get_string(
                    guild_id,
                    "taco_gift_success",
                    user=ctx.author.mention,
                    touser=member.mention,
                    amount=amount,
                    taco_word=tacos_word,
                    reason=reason_msg,
                ),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT,
            )

            await self.discord_helper.taco_give_user(
                guild_id, ctx.author, member, reason_msg, tacotypes.TacoTypes.CUSTOM, taco_amount=amount
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel.id else None,
                userId=ctx.author.id,
                command="tacos",
                subcommand="give",
                args=[{"type": "command"}, {"user_id": member.id}, {"amount": amount}, {"reason": reason_msg}],
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @tacos.command()
    async def count(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id
                await ctx.message.delete()
            # get taco count for message author
            taco_count = self.tacos_db.get_tacos_count(guild_id, ctx.author.id)
            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if taco_count is None:
                taco_count = 0
            if taco_count == 0 or taco_count > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")
            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "taco_count_title"),
                message=self.settings.get_string(
                    guild_id, "taco_count_message", user=ctx.author.mention, count=taco_count, taco_word=tacos_word
                ),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel.id else None,
                userId=ctx.author.id,
                command="tacos",
                subcommand="count",
                args=[{"type": "command"}],
            )
        except Exception as e:
            await ctx.message.delete()
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @tacos.command()
    @commands.guild_only()
    async def gift(self, ctx, member: discord.Member, amount: int, *, reason: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            # get taco count for message author
            await ctx.message.delete()
            taco_settings = self.get_tacos_settings(guild_id)

            # if the user that ran the command is the same as member, then exit the function
            if ctx.author.id == member.id:
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(guild_id, "error"),
                    message=self.settings.get_string(guild_id, "taco_self_gift_message", user=ctx.author.mention),
                    footer=self.settings.get_string(
                        guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT
                    ),
                    delete_after=self.SELF_DESTRUCT_TIMEOUT,
                )
                return
            max_gift_tacos: int = taco_settings.get("max_gift_tacos", 10)
            max_gift_taco_timespan = taco_settings.get("max_gift_taco_timespan", 86400)
            # get the total number of tacos the user has gifted in the last 24 hours
            total_gifted: int = self.tacos_db.get_total_gifted_tacos(
                ctx.guild.id, ctx.author.id, max_gift_taco_timespan
            )
            remaining_gifts = max_gift_tacos - total_gifted

            tacos_word = self.settings.get_string(guild_id, "taco_plural")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_singular")

            if remaining_gifts <= 0:
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(guild_id, "taco_gift_title"),
                    message=self.settings.get_string(
                        guild_id, "taco_gift_maximum", max=max_gift_tacos, taco_word=tacos_word
                    ),
                    delete_after=30,
                )
                return
            if amount <= 0 or amount > remaining_gifts:
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(guild_id, "taco_gift_title"),
                    message=self.settings.get_string(
                        guild_id,
                        "taco_gift_limit_exceeded",
                        user=ctx.author.mention,
                        remaining=remaining_gifts,
                        taco_word=tacos_word,
                    ),
                    footer=self.settings.get_string(
                        guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT
                    ),
                    delete_after=self.SELF_DESTRUCT_TIMEOUT,
                )
                return

            reason_msg = self.settings.get_string(guild_id, "taco_reason_default")
            if reason:
                reason_msg = f"{reason}"

            self.tacos_db.add_taco_gift(ctx.guild.id, ctx.author.id, amount)
            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "taco_gift_title"),
                message=self.settings.get_string(
                    guild_id,
                    "taco_gift_success",
                    user=ctx.message.author.mention,
                    touser=member.mention,
                    amount=amount,
                    taco_word=tacos_word,
                    reason=reason_msg,
                ),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT,
            )

            await self.discord_helper.taco_give_user(
                guild_id, ctx.author, member, reason_msg, tacotypes.TacoTypes.CUSTOM, taco_amount=amount
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel.id else None,
                userId=ctx.author.id,
                command="tacos",
                subcommand="gift",
                args=[{"type": "command"}, {"user_id": member.id}, {"amount": amount}, {"reason": reason_msg}],
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        _method = inspect.stack()[0][3]
        member = message.author
        try:
            # if we are in a guild
            if message.guild:
                guild_id = message.guild.id

                if not member or member.bot or member.system:
                    return

                if message.type == discord.MessageType.premium_guild_subscription:
                    # add tacos to user that boosted the server
                    await self.discord_helper.taco_give_user(
                        guild_id,
                        self.bot.user,
                        member,
                        self.settings.get_string(guild_id, "taco_reason_boost"),
                        tacotypes.TacoTypes.BOOST,
                    )
                    return

                if message.type == discord.MessageType.default:
                    try:
                        if message.reference is not None:
                            ref = message.reference.resolved
                            if ref is None:
                                return
                            if ref.author == message.author or ref.author == self.bot.user:
                                self.log.debug(
                                    guild_id,
                                    f"{self._module}.{self._class}.{_method}",
                                    f"Ignoring message reference from {ref.author}",
                                )
                                return
                            # it is a reply to another user
                            await self.discord_helper.taco_give_user(
                                guild_id,
                                self.bot.user,
                                member,
                                self.settings.get_string(guild_id, "taco_reason_reply", user=ref.author.name),
                                tacotypes.TacoTypes.REPLY,
                            )

                    except Exception as e:
                        self.log.error(
                            guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc()
                        )
                        return

            # if we are in a DM
            else:
                return
        except Exception as ex:
            self.log.error(member.guild.id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload) -> None:
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:
            if payload.event_type != 'REACTION_ADD':
                return

            taco_settings = self.get_tacos_settings(guild_id)

            reaction_emojis = taco_settings.get("reaction_emojis", ["🌮"])
            if str(payload.emoji) not in reaction_emojis:
                return

            self.log.debug(
                guild_id, f"{self._module}.{self._class}.{_method}", f"{payload.emoji} added to {payload.message_id}"
            )

            if str(payload.emoji) in reaction_emojis:
                user = await self.discord_helper.get_or_fetch_user(payload.user_id)
                # ignore if the user is a bot or system
                if not user or user.bot or user.system:
                    return
                channel = await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                # if the message is from a bot, or reacted by the author, ignore it
                if message.author.bot or message.author.id == user.id:
                    return

                has_reacted = self.tacos_db.get_taco_reaction(guild_id, user.id, channel.id, message.id)
                if has_reacted:
                    return

                reaction_count = taco_settings.get("reaction_count", 1)
                # reaction_reward_count = taco_settings["reaction_reward_count"]

                max_gift_tacos = taco_settings.get("max_gift_tacos", 10)
                max_gift_taco_timespan = taco_settings.get("max_gift_taco_timespan", 86400)
                # get the total number of tacos the user has gifted in the last 24 hours
                total_gifted = self.tacos_db.get_total_gifted_tacos(guild_id, user.id, max_gift_taco_timespan)
                # log the total number of tacos the user has gifted
                remaining_gifts = max_gift_tacos - total_gifted
                # track the user's taco reaction
                self.tacos_db.add_taco_reaction(guild_id, user.id, channel.id, message.id)
                # # give the user the reaction reward tacos
                await self.discord_helper.taco_give_user(
                    guild_id,
                    user,
                    message.author,
                    self.settings.get_string(guild_id, "taco_reason_react", user=message.author.name),
                    tacotypes.TacoTypes.REACT_REWARD,
                )

                self.tracking_db.track_command_usage(
                    guildId=guild_id,
                    channelId=payload.channel_id if payload.channel_id else None,
                    userId=payload.user_id,
                    command="tacos",
                    subcommand="reaction",
                    args=[
                        {"type": "reaction"},
                        {
                            "payload": {
                                "message_id": str(payload.message_id),
                                "channel_id": str(payload.channel_id),
                                "guild_id": str(payload.guild_id),
                                "user_id": str(payload.user_id),
                                "emoji": str(payload.emoji),
                                "event_type": payload.event_type,
                                # "burst": payload.burst,
                            }
                        },
                    ],
                )

                if reaction_count <= remaining_gifts:
                    # track that the user has gifted tacos via reactions
                    self.tacos_db.add_taco_gift(guild_id, user.id, reaction_count)
                    # give taco giver tacos too
                    await self.discord_helper.taco_give_user(
                        guild_id,
                        self.bot.user,
                        user,
                        self.settings.get_string(guild_id, "taco_reason_react", user=message.author.name),
                        tacotypes.TacoTypes.REACTION,
                    )
                # else:
                #     # log that the user cannot gift anymore tacos via reactions
                #     self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{user} cannot gift anymore tacos. remaining gifts: {remaining_gifts}")
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

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
    await bot.add_cog(Tacos(bot))
