import typing

from lib.models.DiscordUser import DiscordUser
from lib.models.DiscordRole import DiscordRole
from lib.models.openapi import openapi_type_alias


DiscordMentionable: typing.TypeAlias = typing.Union[DiscordRole, DiscordUser]

openapi_type_alias(
    "DiscordMentionable",
    description="Represents a Discord mentionable entity.",
    managed=True,
)(typing.cast(typing.Any, DiscordMentionable))
