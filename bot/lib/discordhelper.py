"""DiscordHelper Facade

Backward-compatible facade that delegates to specialized helper classes.

⚠️ DEPRECATED: This class is deprecated and will be removed in a future version.
Prefer importing specific helpers from bot.lib.helpers instead.

Migration Guide: See docs/refactoring/discordhelper_migration_guide.md

New Helpers:
- EntityHelper: Discord entity fetching (users, members, roles, channels)
- MessageHelper: Message operations and notifications
- PromptHelper: User interaction prompts
- RoleHelper: Bulk role operations
- TacoHelper: Taco system operations
- ContextHelper: Context object creation

Example:
    # Old (deprecated):
    from bot.lib.discordhelper import DiscordHelper
    helper = DiscordHelper(bot)

    # New (recommended):
    from bot.lib.helpers import EntityHelper, PromptHelper
    entity_helper = EntityHelper(bot)
    prompt_helper = PromptHelper(bot)

Deprecation Timeline:
- Phase 4 (Nov 2025): Facade implemented, migration guide published
- Phase 5-8 (Nov-Dec 2025): All internal code migrated to new helpers
- Phase 9 (6-12 months): Facade removed (breaking change)
"""

import typing

import discord
from bot.lib.enums import tacotypes
from bot.lib.helpers import ContextHelper, EntityHelper, MessageHelper, PromptHelper, RoleHelper, TacoHelper


class DiscordHelper:
    """Legacy facade that delegates to new helper classes.

    ⚠️ DEPRECATED: Use specific helpers from bot.lib.helpers instead.

    This facade maintains backward compatibility during migration.
    See docs/refactoring/discordhelper_migration_guide.md for migration patterns.

    Attributes:
        entity_helper: EntityHelper instance for Discord entity operations
        message_helper: MessageHelper instance for message operations
        prompt_helper: PromptHelper instance for user prompts
        role_helper: RoleHelper instance for role operations
        taco_helper: TacoHelper instance for taco system
        context_helper: ContextHelper instance for context creation
    """

    def __init__(self, bot) -> None:
        self.bot = bot

        # Instantiate helpers
        self.entity_helper = EntityHelper(bot)
        self.message_helper = MessageHelper(bot)
        self.prompt_helper = PromptHelper(bot)
        self.role_helper = RoleHelper(bot)
        self.taco_helper = TacoHelper(bot, entity_helper=self.entity_helper)
        self.context_helper = ContextHelper()

        # Expose legacy properties for backward compatibility
        self.settings = self.entity_helper.settings
        self.log = self.entity_helper.log
        self.messaging = self.message_helper.messaging
        self.tacos_db = self.taco_helper.tacos_db

    # Context utilities
    def create_context(self, **kwargs):
        return self.context_helper.create_context(**kwargs)

    # Message operations
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
        return await self.message_helper.move_message(
            message,
            targetChannel,
            author=author,
            who=who,
            reason=reason,
            fields=fields,
            remove_fields=remove_fields,
            color=color,
            delete_original=delete_original,
        )

    async def notify_bot_not_initialized(self, ctx, subcommand: typing.Optional[str] = None):
        return await self.message_helper.notify_bot_not_initialized(ctx, subcommand=subcommand)

    # Taco operations
    async def taco_give_user(
        self,
        guildId: int,
        fromUser: typing.Union[discord.User, discord.Member],
        toUser: typing.Union[discord.User, discord.Member],
        reason: typing.Optional[str],
        give_type: tacotypes.TacoTypes = tacotypes.TacoTypes.CUSTOM,
        taco_amount: int = 1,
    ) -> int:
        return await self.taco_helper.give_tacos(
            guildId=guildId,
            fromUser=fromUser,
            toUser=toUser,
            reason=reason,
            give_type=give_type,
            taco_amount=taco_amount,
        )

    async def taco_purge_log(
        self,
        guild_id: int,
        toMember: typing.Union[discord.User, discord.Member],
        fromMember: typing.Union[discord.User, discord.Member],
        reason: str,
    ):
        return await self.taco_helper.log_taco_purge(guild_id, toMember, fromMember, reason)

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
        return await self.taco_helper.log_taco_transaction(
            guild_id, toMember, fromMember, count, total_tacos, reason, type
        )

    def _get_tacos_settings(self, guildId: int = 0) -> dict:
        return self.taco_helper.get_taco_settings(guildId)

    # Entity fetching
    async def get_or_fetch_user(self, userId: int):
        return await self.entity_helper.get_or_fetch_user(userId)

    async def get_or_fetch_member(self, guildId: int, userId: int):
        return await self.entity_helper.get_or_fetch_member(guildId, userId)

    async def get_or_fetch_role(self, guild: discord.Guild, roleId: int):
        return await self.entity_helper.get_or_fetch_role(guild, roleId)

    async def get_or_fetch_channel(self, channelId: int):
        return await self.entity_helper.get_or_fetch_channel(channelId)

    def get_by_name_or_id(self, iterable, nameOrId):
        return self.entity_helper.get_by_name_or_id(iterable, nameOrId)

    # Prompt operations
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
        kwargs: dict = {"title": title, "timeout": timeout, "fields": fields}
        if thumbnail is not None:
            kwargs["thumbnail"] = thumbnail
        if image is not None:
            kwargs["image"] = image
        if content is not None:
            kwargs["content"] = content
        if result_callback is not None:
            kwargs["result_callback"] = result_callback

        return await self.prompt_helper.ask_yes_no(ctx, targetChannel, question, **kwargs)

    async def ask_channel_by_name_or_id(
        self, ctx, title: str = "TacoBot", description: str = "Enter the name of the channel", timeout: int = 60
    ):
        return await self.prompt_helper.ask_channel_by_name_or_id(
            ctx, title=title, description=description, timeout=timeout
        )

    async def ask_channel(
        self,
        ctx,
        title: str = "Choose Channel",
        message: str = "Please choose a channel.",
        allow_none: bool = False,
        timeout: int = 60,
        callback=None,
    ):
        return await self.prompt_helper.ask_channel(
            ctx, title=title, message=message, allow_none=allow_none, timeout=timeout, callback=callback
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
        return await self.prompt_helper.ask_number(
            ctx, title=title, message=message, min_value=min_value, max_value=max_value, timeout=timeout
        )

    async def ask_text(
        self,
        ctx,
        targetChannel,
        title: str = "Enter Text Response",
        message: str = "Please enter your response.",
        timeout: int = 60,
        color=None,
    ) -> typing.Union[str, None]:
        return await self.prompt_helper.ask_text(
            ctx, targetChannel, title=title, message=message, timeout=timeout, color=color
        )

    async def ask_for_image_or_text(
        self,
        ctx,
        targetChannel,
        title: str = "Enter Text Response",
        message: str = "Please enter your response.",
        timeout: int = 60,
        color=None,
    ):
        return await self.prompt_helper.ask_for_image_or_text(
            ctx, targetChannel, title=title, message=message, timeout=timeout, color=color
        )

    async def ask_role_list(
        self,
        ctx,
        title: str = "Choose Role",
        message: str = "Please choose a role.",
        allow_none: bool = False,
        exclude_roles: typing.Optional[list] = None,
        timeout: int = 60,
        select_callback: typing.Optional[typing.Callable] = None,
    ):
        kwargs: dict = {"title": title, "message": message, "allow_none": allow_none, "timeout": timeout}
        if exclude_roles is not None:
            kwargs["exclude_roles"] = exclude_roles
        if select_callback is not None:
            kwargs["select_callback"] = select_callback

        return await self.prompt_helper.ask_role_list(ctx, **kwargs)

    # Role operations
    async def add_remove_roles(
        self, user: discord.Member, check_list: list, add_list: list, remove_list: list, allow_everyone: bool = False
    ) -> None:
        return await self.role_helper.add_remove_roles(
            user, check_list=check_list, add_list=add_list, remove_list=remove_list, allow_everyone=allow_everyone
        )
