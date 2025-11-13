import asyncio
import inspect
import os
import traceback
import typing

import discord
from bot.lib import logger, utils
from bot.lib.ChannelSelect import ChannelSelectView
from bot.lib.enums import loglevel
from bot.lib.helpers.message_helper import MessageHelper
from bot.lib.models.textwithattachments import TextWithAttachments
from bot.lib.RoleSelectView import RoleSelect, RoleSelectView
from bot.lib.settings import Settings
from bot.lib.YesOrNoView import YesOrNoView


class PromptHelper:
    """
    Helper class for user interaction prompts and input collection.

    This class handles all user-facing prompts for text input, number input,
    yes/no confirmations, channel selection, role selection, and image/text collection.
    """

    def __init__(self, bot, settings: Settings, message_helper: MessageHelper) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings
        self.bot = bot

        self.message_helper = message_helper
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

    def get_by_name_or_id(self, iterable, nameOrId: typing.Union[int, str]):
        """Get an item from an iterable by name or ID."""
        result = None
        if isinstance(nameOrId, int):
            result = discord.utils.get(iterable, id=nameOrId)
        elif isinstance(nameOrId, str):
            if nameOrId.isnumeric():
                result = discord.utils.get(iterable, id=int(nameOrId))
            else:
                result = discord.utils.get(iterable, name=nameOrId)
        return result

    async def ask_yes_no(
        self,
        ctx,
        targetChannel,
        question: str,
        title: str = "Yes or No?",
        timeout: int = 60,
        fields=None,
        thumbnail: typing.Optional[str] = None,
        image: typing.Optional[str] = None,
        content: typing.Optional[str] = None,
        result_callback: typing.Optional[typing.Callable] = None,
    ):
        """
        Display a yes/no confirmation prompt with buttons.

        Args:
            ctx: The command context
            targetChannel: Channel to send the prompt to
            question: The question to ask
            title: Title of the embed (default: "Yes or No?")
            timeout: Timeout in seconds (default: 60)
            fields: Optional embed fields
            thumbnail: Optional thumbnail URL
            image: Optional image URL
            content: Optional message content (outside embed)
            result_callback: Callback function called with boolean result
        """
        channel = targetChannel if targetChannel else ctx.channel if ctx.channel else ctx.author

        async def answer_callback(caller: YesOrNoView, interaction: discord.Interaction):
            if interaction is None or interaction.data is None:
                return
            result_id = interaction.data["custom_id"]  # type: ignore
            result = utils.str2bool(result_id)
            if result_callback:
                await result_callback(result)

        async def timeout_callback(caller: YesOrNoView, interaction: discord.Interaction):
            await self.message_helper.send_embed(
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
        await self.message_helper.send_embed(
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
        """
        Ask user to manually enter a channel name or ID.

        Args:
            ctx: The command context
            title: Title of the embed (default: "TacoBot")
            description: Description/prompt text
            timeout: Timeout in seconds (default: 60)

        Returns:
            The selected channel object, or None if not found/timeout
        """
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

            channel_ask = await self.message_helper.send_embed(
                target_channel,
                title,
                f"{description}",
                delete_after=timeout,
                footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
            )
            try:
                channelResp = await self.bot.wait_for("message", check=check_channel, timeout=timeout)
            except asyncio.TimeoutError:
                await self.message_helper.send_embed(
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
        """
        Display a channel selection dropdown.

        Args:
            ctx: The command context
            title: Title of the embed (default: "Choose Channel")
            message: Description/prompt text
            allow_none: Whether to allow "None" selection (default: False)
            timeout: Timeout in seconds (default: 60)
            callback: Callback function called with selected channel
        """
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        channels = [c for c in ctx.guild.channels if c.type == discord.ChannelType.text]
        channels.sort(key=lambda c: c.position)

        async def select_callback(select: discord.ui.Select, interaction: discord.Interaction):
            # if not the user that triggered the interaction, ignore
            if interaction.user.id != ctx.author.id:
                return
            if interaction is None or interaction.message is None:
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
                await self.message_helper.send_embed(
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
                await self.message_helper.send_embed(
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
                await self.message_helper.send_embed(
                    ctx.channel,
                    title,
                    self.settings.get_string(guild_id, "unknown_channel", user=ctx.author.mention, channel_id=chan_id),
                    delete_after=5,
                )
                if callback:
                    await callback(None)
                return

        async def select_timeout():
            await self.message_helper.send_embed(
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
        await self.message_helper.send_embed(
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
    ) -> typing.Optional[int]:
        """
        Ask user to enter a number within a range.

        Args:
            ctx: The command context
            title: Title of the embed (default: "Enter Number")
            message: Description/prompt text
            min_value: Minimum allowed value (default: 0)
            max_value: Maximum allowed value (default: 100)
            timeout: Timeout in seconds (default: 60)

        Returns:
            The entered number, or None if timeout/invalid
        """
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

        number_ask = await self.message_helper.send_embed(
            ctx.channel,
            title,
            f"{message}",
            delete_after=timeout,
            footer=self.settings.get_string(guild_id, "footer_XX_seconds", seconds=timeout),
        )
        try:
            numberResp = await self.bot.wait_for("message", check=check_range, timeout=timeout)
        except asyncio.TimeoutError:
            await self.message_helper.send_embed(
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
        """
        Ask user to enter text.

        Args:
            ctx: The command context
            targetChannel: Channel to send the prompt to
            title: Title of the embed (default: "Enter Text Response")
            message: Description/prompt text
            timeout: Timeout in seconds (default: 60)
            color: Optional embed color

        Returns:
            The entered text, or None if timeout
        """

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

        text_ask = await self.message_helper.send_embed(
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
            await self.message_helper.send_embed(
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
        """
        Ask user to enter text and/or upload images.

        Args:
            ctx: The command context
            targetChannel: Channel to send the prompt to
            title: Title of the embed (default: "Enter Text Response")
            message: Description/prompt text
            timeout: Timeout in seconds (default: 60)
            color: Optional embed color

        Returns:
            TextWithAttachments object containing text and attachments, or None if timeout
        """

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

        ask_image_or_text = await self.message_helper.send_embed(
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
            await self.message_helper.send_embed(
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
        exclude_roles: typing.Optional[list] = None,
        timeout: int = 60,
        select_callback: typing.Optional[typing.Callable] = None,
        # timeout_callback: typing.Callable = None,
    ) -> typing.Union[discord.Role, None]:
        """
        Display a role selection dropdown.

        Args:
            ctx: The command context
            title: Title of the embed (default: "Choose Role")
            message: Description/prompt text
            allow_none: Whether to allow "None" selection (default: False)
            exclude_roles: List of roles to exclude from selection
            timeout: Timeout in seconds (default: 60)
            select_callback: Callback function called with selected role

        Returns:
            The selected role, or None if timeout/no selection
        """
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
                        await self.message_helper.send_embed(
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
                        await self.message_helper.send_embed(
                            ctx.channel, title, f"{ctx.author.mention}, Unknown Role.", delete_after=5
                        )
                        await select_callback(None)
                        return
                else:
                    await select_callback(None)

        async def timeout_callback(select: RoleSelect, interaction: discord.Interaction):
            await interaction.delete_original_response()
            await self.message_helper.send_embed(
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

        await self.message_helper.send_embed(
            ctx.channel,
            title,
            message,
            delete_after=timeout,
            footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout),
            view=role_view,
        )
