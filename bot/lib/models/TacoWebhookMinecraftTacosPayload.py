import typing

from bot.lib.models.openapi import openapi


@openapi.component("TacoWebhookMinecraftTacosPayload", description="Payload that is sent to give a Minecraft user tacos.")
@openapi.property("guild_id", description="The ID of the guild where the tacos are being sent.")
@openapi.property("from_user", description="The user who is sending the tacos.")
@openapi.property("to_user_id", description="The ID of the user who is receiving the tacos.")
@openapi.property("amount", description="The number of tacos being sent.")
@openapi.property("reason", description="The reason for sending the tacos.")
@openapi.property("type", description="The event type for giving the tacos to the user.")
@openapi.managed()
class TacoWebhookMinecraftTacosPayload:
    """Payload that is sent to give a Minecraft user tacos."""

    def __init__(self, payload: dict):
        self.guild_id: str = payload.get("guild_id", "")
        self.from_user: str = payload.get("from_user", "")
        self.to_user_id: str = payload.get("to_user_id", "")
        self.amount: int = payload.get("amount", 0)
        self.reason: str = payload.get("reason", "")
        self.type: typing.Literal['login', 'custom'] = payload.get("type", "")
