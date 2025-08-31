import asyncio
import collections
import inspect
import os
import traceback
import typing

import discord
from bot.lib import logger, settings, utils
from bot.lib.ChannelSelect import ChannelSelectView
from bot.lib.enums import loglevel, tacotypes
from bot.lib.messaging import Messaging
from bot.lib.models.textwithattachments import TextWithAttachments
from bot.lib.mongodb.permissions import PermissionsDatabase
from bot.lib.mongodb.tacos import TacosDatabase
from bot.lib.RoleSelectView import RoleSelect, RoleSelectView
from bot.lib.YesOrNoView import YesOrNoView


class DiscordHelper:
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        self.bot = bot

        self.tacos_db = TacosDatabase()
        self.permissions_db = PermissionsDatabase()
        self.messaging = Messaging(bot=self.bot)
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)


    def has_permission(self, guild: int, user: typing.Union[discord.User, discord.Member], permission: str) -> bool:
        _method = inspect.stack()[0][3]
        try:
            # check the database if the user has the permission defined.
            return self.permissions_db.has_user_permission(guild, user.id, permission)
        except Exception as e:
            self.log.error(guild, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return False

    def create_context(
        self, bot=None, author=None, guild=None, channel=None, message=None, invoked_subcommand=None, **kwargs
    ):
        ctx_dict = {
            "bot": bot,
            "author": author,
            "guild": guild,
            "channel": channel,
            "message": message,
            "invoked_subcommand": invoked_subcommand,
        }
        merged_ctx = {**ctx_dict, **kwargs}
        ctx = collections.namedtuple("Context", merged_ctx.keys())(*merged_ctx.values())
        return ctx

    async def move_message(
        self,
        message,
        targetChannel,
        author: typing.Optional[discord.User] = None,
        who: typing.Optional[discord.User] = None,
        reason: typing.Optional[str] = None,
        fields: typing.Optional[list[dict[str, typing.Any]]] = None,
        remove_fields: typing.Optional[list[dict[str, typing.Any]]] = None,
        color: typing.Optional[int] = None,
        delete_original: bool = False,
    ) -> typing.Union[discord.Message, None]:
        _method = inspect.stack()[0][3]
        if not message:
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", "No message to move")
            return
        if not targetChannel:
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", "No target channel to move message to")
            return
        target_author: typing.Optional[discord.User] = author
        if not target_author:
            target_author = message.author

        if not message.guild:
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Message is not from a guild")
            return
        guild_id = message.guild.id

        try:
            content = ""
            if len(message.embeds) == 0:
                description = f"{message.content}"
                title = ""
                embed_fields = []
                image = None
            else:
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Message has embeds")
                embed = message.embeds[0]
                title = embed.title
                if embed.description is None or embed.description == "":
                    description = ""
                else:
                    description = f"{embed.description}"
                content = message.content
                # lib3ration 500 bits: oh look a Darth Fajitas
                embed_fields = embed.fields
                if embed.image is not None and embed.image != "":
                    image = embed.image.url
                else:
                    image = None

                if color is None and embed.color is not None:
                    color = embed.color

            footer = None
            if who:
                footer = f"{self.settings.get_string(guildId=guild_id,key='moved_by',user=f'{utils.get_user_display_name(who)}')} - {reason or self.settings.get_string(guildId=guild_id, key='no_reason')}"

            if color is None:
                color = 0x7289DA

            target_embed = discord.Embed(title=title, description=description, color=color)
            if target_author:
                target_embed.set_author(
                    name=target_author.name, icon_url=target_author.avatar.url if target_author.avatar else None
                )
            if footer:
                target_embed.set_footer(text=footer)
            else:
                target_embed.set_footer(
                    text=self.settings.get_string(
                        guild_id,
                        "developed_by",
                        user=self.settings.get('author', "Unknown"),
                        bot_name=self.settings.get('name', "Unknown"),
                        version=self.settings.get('version', "Unknown"),
                    )
                )
            if remove_fields is None:
                remove_fields = []

            if image is not None:
                target_embed.set_image(url=image)

            if embed_fields is not None:
                for f in [ef for ef in embed_fields if ef.name not in [rfi["name"] for rfi in remove_fields]]:
                    target_embed.add_field(name=f.name, value=f.value, inline=f.inline)
            if fields is not None:
                for f in [rf for rf in fields if rf["name"] not in [rfi["name"] for rfi in remove_fields]]:
                    target_embed.add_field(
                        name=f["name"], value=f["value"], inline=f["inline"] if "inline" in f else False
                    )

            files = [await a.to_file() for a in message.attachments]

            if len(files) > 0 or target_embed is not None:
                moved_message = await targetChannel.send(content=content, files=files, embed=target_embed)
                # delete the original message because we are moving the content to a new channel
                if delete_original:
                    await message.delete()
                return moved_message
            else:
                return None

        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

    async def notify_bot_not_initialized(self, ctx, subcommand: typing.Optional[str] = None):
        channel = ctx.channel
        if not channel:
            channel = ctx.author
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        if not ctx.author.guild_permissions.administrator:
            await self.messaging.send_embed(
                ctx.channel,
                self.settings.get_string(guild_id, "error"),
                self.settings.get_string(guild_id, "not_initialized_user", user=ctx.author.mention),
                delete_after=30,
            )
        else:
            # get the bot's prefix
            prefix = await self.bot.get_prefix(ctx.message)[0]
            await self.messaging.send_embed(
                ctx.channel,
                self.settings.get_string(guild_id, "error"),
                self.settings.get_string(
                    guild_id, "not_initialized_admin", user=ctx.author.mention, prefix=prefix, subcommand=subcommand
                ),
                delete_after=30,
            )

    async def taco_give_user(
        self,
        guildId: int,
        fromUser: typing.Union[discord.User, discord.Member],
        toUser: typing.Union[discord.User, discord.Member],
        reason: typing.Optional[str],
        give_type: tacotypes.TacoTypes = tacotypes.TacoTypes.CUSTOM,
        taco_amount: int = 1,
    ):
        _method = inspect.stack()[0][3]
        try:
            # get taco settings
            taco_settings = self._get_tacos_settings(guildId=guildId)
            taco_count = taco_amount
            taco_type_key = tacotypes.TacoTypes.get_string_from_taco_type(give_type)
            if taco_type_key not in taco_settings:
                self.log.debug(
                    guildId,
                    f"{self._module}.{self._class}.{_method}",
                    f"Key {taco_type_key} not found in taco settings. Using taco_amount ({taco_amount}) as taco count",
                )
                taco_count = taco_count
            else:
                taco_count = taco_settings.get(taco_type_key, taco_amount)

            reason_msg = reason if reason else self.settings.get_string(guildId, "no_reason")

            total_taco_count = self.tacos_db.add_tacos(guildId, toUser.id, taco_count)
            await self.tacos_log(
                guild_id=guildId,
                toMember=toUser,
                fromMember=fromUser,
                count=taco_count,
                total_tacos=total_taco_count,
                reason=reason_msg,
                type=give_type,
            )

            self.tacos_db.track_tacos_log(
                guildId=guildId,
                toUserId=toUser.id,
                fromUserId=fromUser.id,
                count=taco_count,
                reason=reason_msg,
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(give_type),
            )
            return total_taco_count
        except Exception as e:
            self.log.error(guildId, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    async def taco_purge_log(
        self,
        guild_id: int,
        toMember: typing.Union[discord.User, discord.Member],
        fromMember: typing.Union[discord.User, discord.Member],
        reason: str,
    ):
        _method = inspect.stack()[0][3]
        try:
            taco_settings = self._get_tacos_settings(guildId=guild_id)
            taco_log_channel_id = taco_settings["taco_log_channel_id"]
            log_channel = await self.get_or_fetch_channel(int(taco_log_channel_id))

            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{fromMember.name} purged all tacos from {toMember.name} for {reason}",
            )
            if log_channel:
                await log_channel.send(
                    self.settings.get_string(
                        guild_id, "tacos_purged_log", touser=toMember.name, fromuser=fromMember.name, reason=reason
                    )
                )
            self.tacos_db.track_tacos_log(
                guildId=guild_id,
                toUserId=toMember.id,
                fromUserId=fromMember.id,
                count=0,
                reason=reason,
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(tacotypes.TacoTypes.PURGE),
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    async def tacos_log(
        self,
        guild_id: int,
        toMember: typing.Union[discord.User, discord.Member],
        fromMember: typing.Union[discord.User, discord.Member],
        count: int,
        total_tacos: int,
        reason: str,
        type: tacotypes.TacoTypes = tacotypes.TacoTypes.CUSTOM,
    ):
        _method = inspect.stack()[0][3]
        try:
            taco_settings = self._get_tacos_settings(guildId=guild_id)
            taco_log_channel_id = taco_settings["taco_log_channel_id"]
            log_channel = await self.get_or_fetch_channel(int(taco_log_channel_id))
            taco_word = self.settings.get_string(guild_id, "taco_plural")
            if count == 1:
                taco_word = self.settings.get_string(guild_id, "taco_singular")

            total_taco_word = self.settings.get_string(guild_id, "taco_plural")
            if total_tacos == 1:
                total_taco_word = self.settings.get_string(guild_id, "taco_singular")

            action = self.settings.get_string(guild_id, "tacos_log_action_received")
            if count < 0:
                action = self.settings.get_string(guild_id, "tacos_log_action_lost")

            positive_count = abs(count)

            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{utils.get_user_display_name(toMember)} {action} {positive_count} {taco_word} from {utils.get_user_display_name(fromMember)} for {reason}",
            )
            if log_channel:
                fields = [
                    {"name": "▶ TO USER", "value": toMember.name},
                    {"name": "◀ FROM USER", "value": fromMember.name},
                    {"name": f"🎬 {action.upper()}", "value": f"{positive_count} {taco_word}"},
                    {"name": "🌮 TOTAL TACOS", "value": f"{total_tacos} {total_taco_word}"},
                    {"name": "ℹ REASON", "value": reason},
                    {"name": "✨ TYPE", "value": type.name},
                ]

                await self.messaging.send_embed(
                    channel=log_channel, title="", message="", fields=fields, author=fromMember
                )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    async def get_or_fetch_user(self, userId: int) -> typing.Union[discord.User, None]:
        _method = inspect.stack()[1][3]
        try:
            if userId:
                user = self.bot.get_user(userId)
                if not user:
                    user = await self.bot.fetch_user(userId)
                return user
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_member(self, guildId: int, userId: int) -> typing.Union[discord.Member, None]:
        _method = inspect.stack()[1][3]
        try:
            if not guildId:
                return None
            guild = self.bot.get_guild(guildId)
            if not guild:
                guild = await self.bot.fetch_guild(guildId)
            if not guild:
                return None

            if userId:
                user = guild.get_member(userId)
                if not user:
                    user = await guild.fetch_member(userId)
                return user
            return None
        except discord.errors.NotFound:
            return None
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_role(self, guild: discord.Guild, roleId: int) -> typing.Union[discord.Role, None]:
        _method = inspect.stack()[1][3]
        try:
            if not guild:
                return None
            if roleId:
                role = guild.get_role(roleId)
                if not role:
                    roles = [r for r in await guild.fetch_roles() if r.id == roleId]
                    if roles and len(roles) > 0:
                        role = roles[0]
                    else:
                        role = None
                return role
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", str(nf), traceback.format_exc())
            return None

    async def get_or_fetch_channel(
        self, channelId: int
    ) -> typing.Optional[typing.Union[discord.TextChannel, discord.DMChannel, discord.Thread]]:
        _method = inspect.stack()[1][3]
        try:
            if channelId:
                chan = self.bot.get_channel(channelId)
                if not chan:
                    chan = await self.bot.fetch_channel(channelId)
                return chan
            else:
                return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"Channel ID: '{channelId}'")
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Bot: '{self.bot.id}' - {self.bot.name}",
                traceback.format_exc(),
            )
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            return None

    def get_by_name_or_id(self, iterable, nameOrId: typing.Union[int, str]):
        if isinstance(nameOrId, str):
            return discord.utils.get(iterable, name=str(nameOrId))
        elif isinstance(nameOrId, int):
            return discord.utils.get(iterable, id=int(nameOrId))
        else:
            return None

    async def ask_yes_no(
        self,
        ctx,
        targetChannel,
        question: str,
        title: str = "Yes or No?",
        timeout: int = 60,
        fields=None,
        thumbnail: str = None,
        image: str = None,
        content: str = None,
        result_callback: typing.Callable = None,
    ):
        channel = targetChannel if targetChannel else ctx.channel if ctx.channel else ctx.author

        async def answer_callback(caller: YesOrNoView, interaction: discord.Interaction):
            result_id = interaction.data["custom_id"]
            result = utils.str2bool(result_id)
            if result_callback:
                await result_callback(result)

        async def timeout_callback(caller: YesOrNoView, interaction: discord.Interaction):
            await self.messaging.send_embed(
                channel=channel,
                title=title,
                message=self.settings.get_string(ctx.guild.id, "took_too_long"),
                delete_after=5,
            )
            if result_callback:
                await result_callback(False)

        yes_no_view = YesOrNoView(
            ctx, answer_callback=answer_callback, timeout=timeout, timeout_callback=timeout_callback
        )
        await self.messaging.send_embed(
            channel,
            title,
            question,
            view=yes_no_view,
            delete_after=timeout,
            thumbnail=thumbnail,
            image=image,
            fields=fields,
            content=content,
            footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
        )
        return

    async def ask_channel_by_name_or_id(
        self, ctx, title: str = "TacoBot", description: str = "Enter the name of the channel", timeout: int = 60
    ):
        _method = inspect.stack()[1][3]
        try:
            guild = ctx.guild
            if not guild:
                return None

            def check_channel(m):
                c = self.get_by_name_or_id(guild.channels, m.content)
                if c:
                    return True
                else:
                    return False

            target_channel = ctx.channel if ctx.channel else ctx.author

            channel_ask = await self.messaging.send_embed(
                target_channel,
                title,
                f"{description}",
                delete_after=timeout,
                footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
            )
            try:
                channelResp = await self.bot.wait_for("message", check=check_channel, timeout=timeout)
            except asyncio.TimeoutError:
                await self.messaging.send_embed(
                    target_channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5
                )
                return None
            else:
                selected_channel = self.get_by_name_or_id(guild.channels, channelResp.content)
                await channelResp.delete()
                await channel_ask.delete()
                return selected_channel
        except Exception as ex:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            return None

    async def ask_channel(
        self,
        ctx,
        title: str = "Choose Channel",
        message: str = "Please choose a channel.",
        allow_none: bool = False,
        timeout: int = 60,
        callback=None,
    ):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        channels = [c for c in ctx.guild.channels if c.type == discord.ChannelType.text]
        channels.sort(key=lambda c: c.position)

        async def select_callback(select: discord.ui.Select, interaction: discord.Interaction):
            # if not the user that triggered the interaction, ignore
            if interaction.user.id != ctx.author.id:
                return
            chan_id = int(select.values[0])
            await interaction.message.delete()

            if chan_id == 0:
                asked_channel = await self.ask_channel_by_name_or_id(
                    ctx, title, self.settings.get_string(guild_id, "ask_name_of_channel"), timeout=timeout
                )
                chan_id = asked_channel.id if asked_channel else None

            if chan_id is None:
                # manual entered channel not found
                await self.messaging.send_embed(
                    ctx.channel,
                    title,
                    self.settings.get_string(guild_id, "unknown_channel", user=ctx.author.mention, channel_id=chan_id),
                    delete_after=5,
                )
                return
            if chan_id == -1:
                # user selected none
                return

            selected_channel = discord.utils.get(ctx.guild.channels, id=chan_id)
            if selected_channel:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"{utils.get_user_display_name(ctx.author)} selected the channel '{selected_channel.name}'",
                )
                await self.messaging.send_embed(
                    ctx.channel,
                    title,
                    self.settings.get_string(
                        guild_id, "selected_channel_message", user=ctx.author.mention, channel=selected_channel.name
                    ),
                    delete_after=5,
                )
                if callback:
                    await callback(selected_channel)
                return
            else:
                await self.messaging.send_embed(
                    ctx.channel,
                    title,
                    self.settings.get_string(guild_id, "unknown_channel", user=ctx.author.mention, channel_id=chan_id),
                    delete_after=5,
                )
                if callback:
                    await callback(None)
                return

        async def select_timeout():
            await self.messaging.send_embed(
                ctx.channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5
            )

        view = ChannelSelectView(
            ctx=ctx,
            placeholder=title,
            channels=channels,
            allow_none=allow_none,
            select_callback=select_callback,
            timeout_callback=select_timeout,
        )
        # action_row = ActionRow(select)
        await self.messaging.send_embed(
            ctx.channel,
            title,
            message,
            delete_after=timeout,
            footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
            view=view,
        )

    async def ask_number(
        self,
        ctx,
        title: str = "Enter Number",
        message: str = "Please enter a number.",
        min_value: int = 0,
        max_value: int = 100,
        timeout: int = 60,
    ) -> int:
        _method = inspect.stack()[1][3]

        def check_user(m):
            same = m.author.id == ctx.author.id
            return same

        def check_range(m):
            if check_user(m):
                if m.content.isnumeric():
                    val = int(m.content)
                    return val >= min_value and val <= max_value
                return False

        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        # channel = ctx.channel if ctx.channel else ctx.author

        number_ask = await self.messaging.send_embed(
            ctx.channel,
            title,
            f"{message}",
            delete_after=timeout,
            footer=self.settings.get_string(guild_id, "footer_XX_seconds", seconds=timeout),
        )
        try:
            numberResp = await self.bot.wait_for("message", check=check_range, timeout=timeout)
        except asyncio.TimeoutError:
            await self.messaging.send_embed(
                ctx.channel, title, self.settings.get_string(guild_id, "took_too_long"), delete_after=5
            )
            return None
        else:
            numberValue = int(numberResp.content)
            try:
                await numberResp.delete()
            except discord.NotFound:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    "Tried to clean up, but the messages were not found.",
                )
            except discord.Forbidden:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    "Tried to clean up, but the bot does not have permissions to delete messages.",
                )
            try:
                await number_ask.delete()
            except discord.NotFound:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    "Tried to clean up, but the messages were not found.",
                )
            except discord.Forbidden:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    "Tried to clean up, but the bot does not have permissions to delete messages.",
                )
        return numberValue

    async def ask_text(
        self,
        ctx,
        targetChannel,
        title: str = "Enter Text Response",
        message: str = "Please enter your response.",
        timeout: int = 60,
        color=None,
    ) -> typing.Union[str, None]:
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same

        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        channel = targetChannel if targetChannel else ctx.channel if ctx.channel else ctx.author
        delete_user_message = True
        if not ctx.guild:
            channel = ctx.author
            delete_user_message = False

        text_ask = await self.messaging.send_embed(
            channel,
            title,
            f"{message}",
            delete_after=timeout,
            footer=self.settings.get_string(guild_id, "footer_XX_seconds", seconds=timeout),
            color=color,
        )
        try:
            textResp = await self.bot.wait_for("message", check=check_user, timeout=timeout)
        except asyncio.TimeoutError:
            await self.messaging.send_embed(
                channel, title, self.settings.get_string(guild_id, "took_too_long"), delete_after=5
            )
            return None
        else:
            if delete_user_message:
                try:
                    await textResp.delete()
                except Exception:
                    pass
            await text_ask.delete()
        return textResp.content

    async def ask_for_image_or_text(
        self,
        ctx,
        targetChannel,
        title: str = "Enter Text Response",
        message: str = "Please enter your response.",
        timeout: int = 60,
        color=None,
    ) -> typing.Union[TextWithAttachments, None]:
        def check_user(m):
            expected_user = m.author.id == ctx.author.id
            # check that the message is in the same channel as the command or the command was sent in a DM channel

            # was it a DM response from the user?
            dm_check = (
                m.guild is None and ctx.author.dm_channel is not None and ctx.author.dm_channel.id == m.channel.id
            )
            # check if the guild is none for the message, which means it was a DM, so we need to make sure the response is in the same DM
            channel_check = m.guild is not None and m.channel.id == ctx.channel.id
            # print(f"dm_check: {dm_check}")
            # print(f"m.channel: {m.channel.id}")
            # print(f"a.channel: {ctx.author.dm_channel.id}")
            # print(f"ctx: {ctx.channel.id}")
            # print(f"targetChannel: {targetChannel.id}")
            return expected_user and (dm_check or channel_check)

        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        channel = targetChannel if targetChannel else ctx.channel if ctx.channel else ctx.author
        delete_user_message = True
        if not ctx.guild:
            channel = ctx.author
            delete_user_message = False

        ask_image_or_text = await self.messaging.send_embed(
            channel,
            title,
            f"{message}",
            delete_after=timeout,
            footer=self.settings.get_string(guild_id, "footer_XX_seconds", seconds=timeout),
            color=color,
        )
        try:
            textResp = await self.bot.wait_for("message", check=check_user, timeout=timeout)
        except asyncio.TimeoutError:
            await self.messaging.send_embed(
                channel, title, self.settings.get_string(guild_id, "took_too_long"), delete_after=5
            )
            return None
        else:
            if delete_user_message:
                try:
                    await textResp.delete()
                except Exception:
                    pass
            await ask_image_or_text.delete()
        return TextWithAttachments(textResp.content, textResp.attachments)

    async def ask_role_list(
        self,
        ctx,
        title: str = "Choose Role",
        message: str = "Please choose a role.",
        allow_none: bool = False,
        exclude_roles: list = None,
        timeout: int = 60,
        select_callback: typing.Callable = None,
        # timeout_callback: typing.Callable = None,
    ) -> typing.Union[discord.Role, None]:
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id

        async def role_select_callback(select: RoleSelect, interaction: discord.Interaction):
            await interaction.delete_original_response()
            if select_callback:
                if select.values:
                    role_id = 0
                    if len(select.values) > 1:
                        role_id = select.values[0]

                    if role_id == 0:
                        await self.messaging.send_embed(
                            ctx.channel, title, f"{ctx.author.mention}, ENTER ROLE NAME", delete_after=5
                        )
                        # need to ask for role name
                        await select_callback(None)
                        return
                        # chan_id = await self.ask_channel_by_name_or_id(ctx, title)

                    selected_role: discord.Role = discord.utils.get(ctx.guild.roles, id=str(select.values[0]))

                    if selected_role:
                        self.log.debug(
                            guild_id,
                            f"{self._module}.{self._class}.{_method}",
                            f"{ctx.author.mention} selected the role '{selected_role.name}'",
                        )
                        await select_callback(selected_role)
                        return
                    else:
                        await self.messaging.send_embed(
                            ctx.channel, title, f"{ctx.author.mention}, Unknown Role.", delete_after=5
                        )
                        await select_callback(None)
                        return
                else:
                    await select_callback(None)

        async def timeout_callback(select: RoleSelect, interaction: discord.Interaction):
            await interaction.delete_original_response()
            await self.messaging.send_embed(
                ctx.channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5
            )

        role_view = RoleSelectView(
            ctx=ctx,
            placeholder=title,
            exclude_roles=exclude_roles,
            select_callback=role_select_callback,
            timeout_callback=timeout_callback,
            timeout=timeout,
        )

        await self.messaging.send_embed(
            ctx.channel,
            title,
            message,
            delete_after=timeout,
            footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
            view=role_view,
        )

    def _get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings

    async def add_remove_roles(
        self, user: discord.Member, check_list: list, add_list: list, remove_list: list, allow_everyone: bool = False
    ) -> None:
        _method = inspect.stack()[1][3]
        if user is None or user.guild is None:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", "User or guild is None")
            return

        guild_id = user.guild.id
        if user.roles:
            # check if the user has any of the watch roles
            user_is_in_watch_role = any([str(r.id) for r in user.roles if str(r.id) in check_list])

            if user_is_in_watch_role or allow_everyone:
                # remove the roles from the user
                if remove_list:
                    role_list = []
                    for role_id in remove_list:
                        role = user.guild.get_role(int(role_id))
                        if role and role in user.roles:
                            role_list.append(role)
                            self.log.info(
                                guild_id,
                                f"{self._module}.{self._class}.{_method}",
                                f"Removed role {role.name} from user {user.display_name}",
                            )

                    if role_list and len(role_list) > 0:
                        try:
                            await user.remove_roles(*role_list)
                        except Exception as e:
                            self.log.warn(
                                guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc()
                            )
                # add the existing roles back to the user
                if add_list:
                    role_list = []
                    for role_id in add_list:
                        role = user.guild.get_role(int(role_id))
                        if role and role not in user.roles:
                            role_list.append(role)
                            self.log.info(
                                guild_id,
                                f"{self._module}.{self._class}.{_method}",
                                f"Added role {role.name} to user {user.display_name}",
                            )

                    if role_list and len(role_list) > 0:
                        try:
                            await user.add_roles(*role_list)
                        except Exception as e:
                            self.log.warn(
                                guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc()
                            )
