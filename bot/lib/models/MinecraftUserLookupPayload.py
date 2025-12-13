import typing

import bot.lib.models.openapi as openapi


@openapi.component("MinecraftUserLookupPayload", description="Payload for looking up a Minecraft user.")
@openapi.property("uuid", description="The UUID of the Minecraft user.")
@openapi.property("username", description="The username of the Minecraft user.")
@openapi.property("user_id", description="The Discord user ID associated with the Minecraft user.")
@openapi.managed()
class MinecraftUserLookupPayload:
    def __init__(self, **kwargs):
        self.uuid = kwargs.get("uuid", "")
        self.username = kwargs.get("username", "")
        self.user_id = kwargs.get("user_id", "")

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "uuid": self.uuid,
            "username": self.username,
            "user_id": self.user_id,
        }

    def is_empty(self) -> bool:
        return self.uuid == "" and self.user_id == "" and self.username == ""


    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "MinecraftUserLookupPayload":
        return MinecraftUserLookupPayload(**data)
