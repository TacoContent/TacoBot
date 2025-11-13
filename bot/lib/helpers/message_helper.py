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
from bot.lib import logger, utils
from bot.lib.enums import loglevel
from bot.lib.settings import Settings
from bot.tacobot import TacoBot


class MessageHelper:
    """Helper class for message manipulation and bot notification messages."""

    def __init__(self, bot: TacoBot, settings: Settings) -> None:
        """Initialize MessageHelper with bot instance.

        Args:
            bot: The Discord bot instance
        """
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]

        self.bot = bot
        self.settings = settings

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

    async def send_embed(
        self,
        channel: typing.Union[
            discord.abc.GuildChannel,
            discord.TextChannel,
            discord.DMChannel,
            discord.GroupChannel,
            discord.Thread,
            # discord.User,
            discord.Member,
            discord.ClientUser,
            discord.abc.Messageable,
        ],
        title: typing.Optional[str] = None,
        message: typing.Optional[str] = None,
        fields: typing.Optional[list[dict[str, typing.Any]]] = None,
        delete_after: typing.Optional[float] = None,
        footer: typing.Optional[typing.Any] = None,
        view: typing.Optional[discord.ui.View] = None,
        color: typing.Optional[int] = 0x7289DA,
        author: typing.Optional[typing.Union[discord.User, discord.Member, discord.ClientUser]] = None,
        thumbnail: typing.Optional[str] = None,
        image: typing.Optional[str] = None,
        url: typing.Optional[str] = "",
        content: typing.Optional[str] = None,
        files: typing.Optional[list] = None,
    ) -> discord.Message:
        if color is None:
            color = 0x7289DA

        guild_id = 0
        if (
            not isinstance(channel, discord.ClientUser)
            and not isinstance(channel, discord.User)
            and not isinstance(channel, discord.abc.Messageable)
        ):
            guild_id = channel.guild.id

        embed = discord.Embed(title=title, description=message, color=color, url=url)
        if author:
            embed.set_author(
                name=f"{utils.get_user_display_name(author)}", icon_url=author.avatar.url if author.avatar else None
            )
        if embed.fields is not None:
            for f in embed.fields:
                embed.add_field(name=f.name, value=f.value, inline=f.inline)
        if fields is not None:
            for f in fields:
                embed.add_field(name=f["name"], value=f["value"], inline=f["inline"] if "inline" in f else False)
        if footer is None:
            embed.set_footer(
                text=self.settings.get_string(
                    guild_id,
                    "developed_by",
                    user=self.settings.get("author", "Unknown"),
                    bot_name=self.settings.get("name", "Unknown"),
                    version=self.settings.get("version", "Unknown"),
                )
            )
        else:
            embed.set_footer(text=footer)

        if thumbnail is not None:
            embed.set_thumbnail(url=thumbnail)
        if image is not None:
            embed.set_image(url=image)
        return await channel.send(  # type: ignore
            content=content, embed=embed, delete_after=delete_after, view=view, files=files  # type: ignore
        )

    async def update_embed(
        self,
        message: typing.Optional[discord.Message] = None,
        title: typing.Optional[str] = None,
        description: typing.Optional[str] = None,
        description_append: typing.Optional[bool] = True,
        fields: typing.Optional[list[dict[str, typing.Any]]] = None,
        content: typing.Optional[str] = None,
        footer: typing.Optional[typing.Any] = None,
        view: typing.Optional[discord.ui.View] = None,
        color: typing.Optional[int] = 0x7289DA,
        author: typing.Optional[typing.Union[discord.User, discord.Member]] = None,
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
        updated_embed = discord.Embed(color=color, title=embed.title, description=f"{description}")
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
                    user=self.settings.get("author", "Unknown"),
                    bot_name=self.settings.get("name", "Unknown"),
                    version=self.settings.get("version", "Unknown"),
                )
            )
        else:
            updated_embed.set_footer(text=footer)

        target_content = message.content
        if content:
            target_content = content

        if author:
            updated_embed.set_author(
                name=f"{utils.get_user_display_name(author)}", icon_url=author.avatar.url if author.avatar else None
            )

        await message.edit(content=target_content, embed=updated_embed, view=view)

    async def notify_of_error(self, ctx):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
        await self.send_embed(
            channel=ctx.channel,
            title=self.settings.get_string(guild_id, "error"),
            message=self.settings.get_string(
                guild_id,
                "error_occurred",
                user=ctx.author.mention if hasattr(ctx, "author") else ctx.user.mention if hasattr(ctx, "user") else "",
            ),
            delete_after=30,
        )

    async def move_message(
        self,
        message,
        targetChannel,
        author: typing.Optional[typing.Union[discord.User, discord.Member, discord.ClientUser]] = None,
        who: typing.Optional[typing.Union[discord.User, discord.Member, discord.ClientUser]] = None,
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

        target_author: typing.Optional[typing.Union[discord.User, discord.Member, discord.ClientUser]] = author
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
            await self.send_embed(
                ctx.channel,
                self.settings.get_string(guild_id, "error"),
                self.settings.get_string(guild_id, "not_initialized_user", user=ctx.author.mention),
                delete_after=30,
            )
        else:
            # get the bot's prefix
            prefix = (await self.bot.get_prefix(ctx.message))[0]
            await self.send_embed(
                ctx.channel,
                self.settings.get_string(guild_id, "error"),
                self.settings.get_string(
                    guild_id, "not_initialized_admin", user=ctx.author.mention, prefix=prefix, subcommand=subcommand
                ),
                delete_after=30,
            )
