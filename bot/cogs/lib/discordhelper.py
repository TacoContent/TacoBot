import async_timeout
import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import collections

from .ChannelSelect import ChannelSelect, ChannelSelectView

from .RoleSelectView import RoleSelectView, RoleSelect

from discord.ext.commands.cooldowns import BucketType
from discord import (
    SelectOption,
    ActionRow,
    SelectMenu,
)
from discord.ui import Button, Select, TextInput

# from interactions import ComponentContext
# from interactions import (
#     Button,
#     SelectMenu,
#     SelectOption,
#     ActionRow
# )
# from discord_slash.utils.manage_components import (
#     create_button,
#     create_actionrow,
#     create_select,
#     create_select_option,
#     wait_for_component,
# )
# from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure

from . import utils
from . import logger
from . import loglevel
from . import settings
from . import mongo
from . import dbprovider
from . import tacotypes
from .models import TextWithAttachments
from .YesOrNoView import YesOrNoView


import inspect


class DiscordHelper:
    def __init__(self, bot):
        self.settings = settings.Settings()
        self.bot = bot
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

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
        author: discord.User = None,
        who: discord.User = None,
        reason: str = None,
        fields=None,
        remove_fields=None,
        color: int = None,
    ):
        if not message:
            self.log.debug(0, "discordhelper.move_message", "No message to move")
            return
        if not targetChannel:
            self.log.debug(0, "discordhelper.move_message", "No target channel to move message to")
            return
        if not author:
            author = message.author

        if not message.guild:
            self.log.debug(0, "discordhelper.move_message", "Message is not from a guild")
            return
        guild_id = message.guild.id

        try:
            if len(message.embeds) == 0:
                self.log.debug(0, "discordhelper.move_message", "Message has no embeds")
                self.log.debug(0, "discordhelper.move_message", f"Message: {message}")
                self.log.debug(0, "discordhelper.move_message", f"Message content: {message.content}")
                description = f"{message.content}"
                title = ""
                embed_fields = []
                image = None
            else:
                self.log.debug(0, "discordhelper.move_message", "Message has embeds")
                embed = message.embeds[0]
                title = embed.title
                if embed.description is None or embed.description == "":
                    description = ""
                else:
                    description = f"{embed.description}"
                # lib3ration 500 bits: oh look a Darth Fajitas
                embed_fields = embed.fields
                if embed.image is not None and embed.image != "":
                    image = embed.image.url
                else:
                    image = None

                if color is None and embed.color is not None:
                    color = embed.color

            if who:
                footer = f"{self.settings.get_string(guild_id, 'moved_by', user=f'{who.name}#{who.discriminator}')} - {reason or self.settings.get_string(guild_id, 'no_reason')}"

            if color is None:
                color = 0x7289DA

            target_embed = discord.Embed(title=title, description=description, color=color)
            target_embed.set_author(name=author.name, icon_url=author.avatar.url)
            if footer:
                target_embed.set_footer(text=footer)
            else:
                target_embed.set_footer(
                    text=self.settings.get_string(
                        guild_id,
                        "developed_by",
                        user=self.settings.author,
                        bot_name=self.settings.name,
                        version=self.settings.version,
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
                await targetChannel.send(files=files, embed=target_embed)
        except Exception as ex:
            self.log.error(0, "discordhelper.move_message", str(ex), traceback.format_exc())

    async def sendEmbed(
        self,
        channel,
        title: str = None,
        message: str = None,
        fields=None,
        delete_after: float = None,
        footer=None,
        view=None,
        color=0x7289DA,
        author: typing.Union[discord.User, discord.Member] = None,
        thumbnail: str = None,
        image: str = None,
        url: str = "",
        content: str = None,
        files: list = None,
    ):
        if color is None:
            color = 0x7289DA
        guild_id = 0

        if hasattr(channel, "guild") and channel.guild:
            guild_id = channel.guild.id

        embed = discord.Embed(title=title, description=message, color=color, url=url)
        if author:
            embed.set_author(name=f"{author.name}#{author.discriminator}", icon_url=author.avatar.url)
        if embed.fields is not None:
            for f in embed.fields:
                embed.add_field(name=f["name"], value=f["value"], inline=f["inline"] if "inline" in f else False)
        if fields is not None:
            for f in fields:
                embed.add_field(name=f["name"], value=f["value"], inline=f["inline"] if "inline" in f else False)
        if footer is None:
            embed.set_footer(
                text=self.settings.get_string(
                    guild_id,
                    "developed_by",
                    user=self.settings.author,
                    bot_name=self.settings.name,
                    version=self.settings.version,
                )
            )
        else:
            embed.set_footer(text=footer)

        if thumbnail is not None:
            embed.set_thumbnail(url=thumbnail)
        if image is not None:
            embed.set_image(url=image)
        return await channel.send(content=content, embed=embed, delete_after=delete_after, view=view, files=files)

    async def updateEmbed(
        self,
        message: discord.Message = None,
        title: str = None,
        description: str = None,
        description_append: bool = True,
        fields: list = None,
        footer: str = None,
        view: discord.ui.View = None,
        color: int = 0x7289DA,
        author: typing.Union[discord.User, discord.Member] = None,
    ):
        if not message or len(message.embeds) == 0:
            return
        if color is None:
            color = 0x7289DA
        guild_id = 0
        if message.guild:
            guild_id = message.guild.id
        embed = message.embeds[0]
        if title is None:
            title = embed.title if embed.title is not None else ""
        if description is not None:
            if description_append:
                edescription = ""
                if embed.description is not None and embed.description != "":
                    edescription = embed.description

                description = edescription + "\n\n" + description
            else:
                description = description
        else:
            if embed.description is not None and embed.description != "":
                description = embed.description
            else:
                description = ""
        updated_embed = discord.Embed(color=color, title=embed.title, description=f"{description}", view=view)
        for f in embed.fields:
            updated_embed.add_field(name=f.name, value=f.value, inline=f.inline)
        if fields is not None:
            for f in fields:
                updated_embed.add_field(
                    name=f["name"], value=f["value"], inline=f["inline"] if "inline" in f else False
                )
        if footer is None:
            updated_embed.set_footer(
                text=self.settings.get_string(
                    guild_id,
                    "developed_by",
                    user=self.settings.author,
                    bot_name=self.settings.name,
                    version=self.settings.version,
                )
            )
        else:
            updated_embed.set_footer(text=footer)

        if author:
            updated_embed.set_author(name=f"{author.name}#{author.discriminator}", icon_url=author.avatar.url)

        await message.edit(embed=updated_embed)

    async def notify_of_error(self, ctx):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
        await self.sendEmbed(
            ctx.channel,
            self.settings.get_string(guild_id, "error"),
            self.settings.get_string(guild_id, "error_ocurred", user=ctx.author.mention),
            delete_after=30,
        )

    async def notify_bot_not_initialized(self, ctx, subcommand: str = None):
        channel = ctx.channel
        if not channel:
            channel = ctx.author
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        if not ctx.author.guild_permissions.administrator:
            await self.sendEmbed(
                ctx.channel,
                self.settings.get_string(guild_id, "error"),
                self.settings.get_string(guild_id, "not_initialized_user", user=ctx.author.mention),
                delete_after=30,
            )
        else:
            # get the bot's prefix
            prefix = await self.bot.get_prefix(ctx.message)[0]
            await self.sendEmbed(
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
        reason: str = None,
        give_type: tacotypes.TacoTypes = tacotypes.TacoTypes.CUSTOM,
        taco_amount: int = 1,
    ):
        _method = inspect.stack()[0][3]
        try:
            # get taco settings
            taco_settings = self.settings.get_settings(self.db, guildId, "tacos")
            if not taco_settings:
                # raise exception if there are no tacos settings
                self.log.error(guildId, "tacos.on_message", f"No tacos settings found for guild {guildId}")
                return
            taco_count = taco_amount

            if give_type != tacotypes.TacoTypes.CUSTOM:
                taco_count = taco_settings[tacotypes.TacoTypes.get_string_from_taco_type(give_type)]
            elif give_type == tacotypes.TacoTypes.CUSTOM:
                taco_count = taco_amount
            else:
                self.log.warn(guildId, "tacos.on_message", f"Invalid taco type {give_type}")
                return

            # only reject <= 0 tacos if it is not custom type
            if taco_count <= 0 and give_type != tacotypes.TacoTypes.CUSTOM:
                self.log.warn(guildId, "tacos.on_message", f"Invalid taco count {taco_count}")
                return

            reason_msg = reason if reason else self.settings.get_string(guildId, "no_reason")

            total_taco_count = self.db.add_tacos(guildId, toUser.id, taco_count)
            await self.tacos_log(
                guild_id=guildId,
                toMember=toUser,
                fromMember=fromUser,
                count=taco_count,
                total_tacos=total_taco_count,
                reason=reason_msg,
            )

            self.db.track_tacos_log(
                guildId=guildId,
                toUserId=toUser.id,
                fromUserId=fromUser.id,
                count=taco_count,
                reason=reason_msg,
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(give_type),
            )
            return total_taco_count
        except Exception as e:
            self.log.error(guildId, _method, str(e), traceback.format_exc())

    async def taco_purge_log(
        self,
        guild_id: int,
        toMember: typing.Union[discord.User, discord.Member],
        fromMember: typing.Union[discord.User, discord.Member],
        reason: str,
    ):
        _method = inspect.stack()[0][3]
        try:

            taco_settings = self.settings.get_settings(self.db, guild_id, "tacos")
            if not taco_settings:
                # raise exception if there are no tacos settings
                raise Exception("No tacos settings found")

            taco_log_channel_id = taco_settings["taco_log_channel_id"]
            log_channel = await self.get_or_fetch_channel(int(taco_log_channel_id))

            self.log.debug(guild_id, _method, f"{fromMember.name} purged all tacos from {toMember.name} for {reason}")
            if log_channel:
                await log_channel.send(
                    self.settings.get_string(
                        guild_id, "tacos_purged_log", touser=toMember.name, fromuser=fromMember.name, reason=reason
                    )
                )
        except Exception as e:
            self.log.error(guild_id, _method, str(e), traceback.format_exc())

    async def tacos_log(
        self,
        guild_id: int,
        toMember: typing.Union[discord.User, discord.Member],
        fromMember: typing.Union[discord.User, discord.Member],
        count: int,
        total_tacos: int,
        reason: str,
    ):
        _method = inspect.stack()[0][3]
        try:

            taco_settings = self.settings.get_settings(self.db, guild_id, "tacos")
            if not taco_settings:
                # raise exception if there are no tacos settings
                raise Exception("No tacos settings found")

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
                _method,
                f"{toMember.name}#{toMember.discriminator} {action} {positive_count} {taco_word} from {fromMember.name}#{fromMember.discriminator} for {reason}",
            )
            if log_channel:

                fields = [
                    {"name": "▶ TO USER", "value": toMember.name},
                    {"name": "◀ FROM USER", "value": fromMember.name},
                    {"name": f"🎬 {action.upper()}", "value": f"{positive_count} {taco_word}"},
                    {"name": "🌮 TOTAL TACOS", "value": f"{total_tacos} {total_taco_word}"},
                    {"name": "ℹ REASON", "value": reason},
                ]

                await self.sendEmbed(channel=log_channel, title="", message="", fields=fields, author=fromMember)
        except Exception as e:
            self.log.error(guild_id, _method, str(e), traceback.format_exc())

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
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
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
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_channel(self, channelId: int) -> typing.Union[discord.TextChannel, None]:
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
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
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
            await self.sendEmbed(
                channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5
            )
            if result_callback:
                await result_callback(False)

        yes_no_view = YesOrNoView(
            ctx, answer_callback=answer_callback, timeout=timeout, timeout_callback=timeout_callback
        )
        await self.sendEmbed(
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

            channel_ask = await self.sendEmbed(
                target_channel,
                title,
                f"{description}",
                delete_after=timeout,
                footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
            )
            try:
                channelResp = await self.bot.wait_for("message", check=check_channel, timeout=timeout)
            except asyncio.TimeoutError:
                await self.sendEmbed(
                    target_channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5
                )
                return None
            else:
                selected_channel = self.get_by_name_or_id(guild.channels, channelResp.content)
                await channelResp.delete()
                await channel_ask.delete()
                return selected_channel
        except Exception as ex:
            self.log.error(ctx.guild.id, _method, str(ex), traceback.format_exc())
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
        options = []
        channels = [c for c in ctx.guild.channels if c.type == discord.ChannelType.text]
        channels.sort(key=lambda c: c.position)
        sub_message = ""

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
                await self.sendEmbed(
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
                    guild_id, _method, f"{ctx.author.mention} selected the channel '{selected_channel.name}'"
                )
                await self.sendEmbed(
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
                await self.sendEmbed(
                    ctx.channel,
                    title,
                    self.settings.get_string(guild_id, "unknown_channel", user=ctx.author.mention, channel_id=chan_id),
                    delete_after=5,
                )
                if callback:
                    await callback(None)
                return

        async def select_timeout():
            await self.sendEmbed(
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
        await self.sendEmbed(
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
    ):
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

        channel = ctx.channel if ctx.channel else ctx.author

        number_ask = await self.sendEmbed(
            ctx.channel,
            title,
            f"{message}",
            delete_after=timeout,
            footer=self.settings.get_string(guild_id, "footer_XX_seconds", seconds=timeout),
        )
        try:
            numberResp = await self.bot.wait_for("message", check=check_range, timeout=timeout)
        except asyncio.TimeoutError:
            await self.sendEmbed(
                ctx.channel, title, self.settings.get_string(guild_id, "took_too_long"), delete_after=5
            )
            return None
        else:
            numberValue = int(numberResp.content)
            try:
                await numberResp.delete()
            except discord.NotFound as e:
                self.log.debug(guild_id, "ask_number", f"Tried to clean up, but the messages were not found.")
            except discord.Forbidden as f:
                self.log.debug(
                    guild_id,
                    "ask_number",
                    f"Tried to clean up, but the bot does not have permissions to delete messages.",
                )
            try:
                await number_ask.delete()
            except discord.NotFound as e:
                self.log.debug(guild_id, "ask_number", f"Tried to clean up, but the messages were not found.")
            except discord.Forbidden as f:
                self.log.debug(
                    guild_id,
                    "ask_number",
                    f"Tried to clean up, but the bot does not have permissions to delete messages.",
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
    ):
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

        text_ask = await self.sendEmbed(
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
            await self.sendEmbed(channel, title, self.settings.get_string(guild_id, "took_too_long"), delete_after=5)
            return None
        else:
            if delete_user_message:
                try:
                    await textResp.delete()
                except:
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
    ):
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

        ask_image_or_text = await self.sendEmbed(
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
            await self.sendEmbed(channel, title, self.settings.get_string(guild_id, "took_too_long"), delete_after=5)
            return None
        else:
            if delete_user_message:
                try:
                    await textResp.delete()
                except:
                    pass
            await ask_image_or_text.delete()
        return TextWithAttachments(textResp.content, textResp.attachments)

        pass

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
    ):
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
                        await self.sendEmbed(
                            ctx.channel, title, f"{ctx.author.mention}, ENTER ROLE NAME", delete_after=5
                        )
                        # need to ask for role name
                        await select_callback(None)
                        return
                        # chan_id = await self.ask_channel_by_name_or_id(ctx, title)

                    selected_role: discord.Role = discord.utils.get(ctx.guild.roles, id=str(select.values[0]))

                    if selected_role:
                        self.log.debug(
                            guild_id, _method, f"{ctx.author.mention} selected the role '{selected_role.name}'"
                        )
                        await select_callback(selected_role)
                        return
                    else:
                        await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, Unknown Role.", delete_after=5)
                        await select_callback(None)
                        return
                else:
                    await select_callback(None)

        async def timeout_callback(select: RoleSelect, interaction: discord.Interaction):
            await interaction.delete_original_response()
            await self.sendEmbed(
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

        await self.sendEmbed(
            ctx.channel,
            title,
            message,
            delete_after=timeout,
            footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
            view=role_view,
        )

    async def is_admin(self, guildId: int, userId: int):
        member = await self.get_or_fetch_member(guildId, userId)
        if not member:
            return False
        # does the user have admin permissions?
        return member.guild_permissions.administrator
