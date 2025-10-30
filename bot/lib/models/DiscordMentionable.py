import typing

from bot.lib.models.openapi import openapi
from lib.models.DiscordRole import DiscordRole
from lib.models.DiscordUser import DiscordUser

DiscordMentionable: typing.TypeAlias = typing.Union[DiscordRole, DiscordUser]

openapi.type_alias("DiscordMentionable", description="Represents a Discord mentionable entity.", managed=True)(
    typing.cast(typing.Any, DiscordMentionable)
)
