import typing

from bot.lib.models.openapi import openapi

TacoMinecraftWorlds: typing.TypeAlias = typing.Literal["taco_atm8", "taco_atm9", "taco_atm10", "taco_atm10-2"]

openapi.type_alias(
    "TacoMinecraftWorlds",
    description="Represents a Minecraft world managed by TacoBot.",
    default="taco_atm10-2",
    managed=True,
)(typing.cast(typing.Any, TacoMinecraftWorlds))
