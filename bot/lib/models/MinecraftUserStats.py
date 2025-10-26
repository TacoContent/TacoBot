import typing

from bot.lib.models.openapi import openapi


@openapi.component("MinecraftUserStatsItem", description="TypedDict for individual Minecraft user statistics item.")
@openapi.managed()
class MinecraftUserStatsItem(typing.Dict[str, int]):
    """TypedDict for individual Minecraft user statistics item."""

    def __init__(self, data: typing.Dict[str, int]):
        super().__init__(data)


@openapi.component("MinecraftUserStats", description="Payload for Minecraft user statistics.")
@openapi.managed()
class MinecraftUserStats(typing.Dict[str, MinecraftUserStatsItem]):
    """Payload for Minecraft user statistics.

    Inherits from `dict` to allow flexible storage of various statistics."""

    def __init__(self, data: typing.Dict[str, MinecraftUserStatsItem]):
        super().__init__(data)
