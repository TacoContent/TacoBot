
import typing

from bot.lib.models import openapi

@openapi.component("MinecraftUserEntry", description="Represents a Minecraft user entry in a guild.")
@openapi.property("guild_id", description="The ID of the guild.")
@openapi.property("user_id", description="The ID of the user.")
@openapi.property("username", description="The username of the Minecraft user.")
@openapi.property("uuid", description="The UUID of the Minecraft user.")
@openapi.property("whitelist", description="Whether the user is whitelisted.")
@openapi.property("op", description="Operator status data for the Minecraft user.")
@openapi.managed()
class MinecraftUserEntry:
    def __init__(self, **kwargs):
        self.guild_id: int = int(kwargs.get("guild_id", "0"))
        self.user_id: int = int(kwargs.get("user_id", "0"))
        self.username: str = kwargs.get("username", "")
        self.whitelist: bool = kwargs.get("whitelist", False)
        self.uuid: str = kwargs.get("uuid", "")
        op = kwargs.get("op", None)
        self.op: typing.Optional[MinecraftUserOpData] = MinecraftUserOpData(**op) if op else None

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        result: typing.Dict[str, typing.Any] = {
            "guild_id": str(self.guild_id),
            "user_id": str(self.user_id),
            "username": self.username,
            "uuid": self.uuid,
            "whitelist": self.whitelist,
        }
        if self.op:
            result["op"] = {
                "enabled": self.op.enabled,
                "level": self.op.level,
                "bypassesPlayerLimit": self.op.bypassesPlayerLimit,
            }
        return result

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftUserEntry":
        result: typing.Dict[str, typing.Any] = {
            "guild_id": str(data.get("guild_id", "0")),
            "user_id": str(data.get("user_id", "0")),
            "username": data.get("username", ""),
            "uuid": data.get("uuid", ""),
            "whitelist": data.get("whitelist", False),
        }
        op = data.get("op", None)
        if op:
            result["op"] = {
                "enabled": op.get("enabled", False),
                "level": op.get("level", 0),
                "bypassesPlayerLimit": op.get("bypassesPlayerLimit", False),
            }
        return MinecraftUserEntry(**result)


@openapi.component("MinecraftUserOpData", description="Operator status data for a Minecraft user.")
@openapi.property("enabled", description="Whether the operator status is enabled.")
@openapi.property("level", description="The operator level, e.g., 4 for admin, 2 for operator.")
@openapi.property("bypassesPlayerLimit", description="Whether the operator bypasses the player limit.")
@openapi.managed()
class MinecraftUserOpData:
    def __init__(self, **kwargs):
        self.enabled: bool = kwargs.get("enabled", False)
        self.level: int = kwargs.get("level", 0)  # e.g., 4 for admin, 2 for operator
        self.bypassesPlayerLimit: bool = kwargs.get("bypassesPlayerLimit", False)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "enabled": self.enabled,
            "level": self.level,
            "bypassesPlayerLimit": self.bypassesPlayerLimit,
        }

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftUserOpData":
        return MinecraftUserOpData(
            enabled=data.get("enabled", False),
            level=data.get("level", 0),
            bypassesPlayerLimit=data.get("bypassesPlayerLimit", False),
        )
