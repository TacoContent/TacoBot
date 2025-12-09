
import typing

from bot.lib.models import openapi

@openapi.component("MinecraftTacoBalance", description="Represents a Minecraft Taco balance.")
@openapi.property("balance", description="The Taco balance of the Minecraft user.")
@openapi.property("uuid", description="The UUID of the Minecraft user.")
@openapi.managed()
class MinecraftTacoBalance:
    def __init__(self, **kwargs):
        self.balance: int = kwargs.get("balance", 0)
        self.uuid: str = kwargs.get("uuid", "")

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {"balance": self.balance, "uuid": self.uuid}

    def is_empty(self) -> bool:
        return self.balance == 0 and self.uuid == ""

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftTacoBalance":
        return cls(balance=data.get("balance", 0), uuid=data.get("uuid", ""))
