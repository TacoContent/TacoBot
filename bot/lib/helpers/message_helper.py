"""MessageHelper - Handles message operations and bot notifications.

This helper class is responsible for:
- Moving/copying messages between channels
- Sending bot initialization error notifications to users/admins
"""

import inspect
import os
import traceback
import typing

import discord
from bot.lib import logger, settings, utils
from bot.lib.enums import loglevel
from bot.lib.messaging import Messaging


class MessageHelper:
    """Helper class for message manipulation and bot notification messages."""

    def __init__(self, bot) -> None:
        """Initialize MessageHelper with bot instance.

        Args:
            bot: The Discord bot instance
        """
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]

        self.bot = bot
        self.settings = settings.Settings()
        self.messaging = Messaging(bot=self.bot)

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

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
        """Move or copy a message to a different channel.

        Args:
            message: The Discord message to move/copy
            targetChannel: The channel to move the message to
            author: Override author for the moved message (defaults to original message author)
            who: User who initiated the move (for footer attribution)
            reason: Reason for moving the message (for footer)
            fields: Additional embed fields to add
            remove_fields: Fields to remove from original embed (by name)
            color: Embed color override
            delete_original: Whether to delete the original message after moving

        Returns:
            The new message in the target channel, or None if move failed
        """
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
        """Send a notification that the bot is not initialized for this guild.

        Sends different messages to admins vs regular users.

        Args:
            ctx: The Discord command context
            subcommand: Optional subcommand name to include in admin message
        """
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
            prefix = (await self.bot.get_prefix(ctx.message))[0]
            await self.messaging.send_embed(
                ctx.channel,
                self.settings.get_string(guild_id, "error"),
                self.settings.get_string(
                    guild_id, "not_initialized_admin", user=ctx.author.mention, prefix=prefix, subcommand=subcommand
                ),
                delete_after=30,
            )
