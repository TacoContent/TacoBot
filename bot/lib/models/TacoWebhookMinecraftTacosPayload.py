
import typing


from bot.lib.models.openapi import openapi_model


@openapi_model("TacoWebhookMinecraftTacosPayload", description="Payload that is sent to give a Minecraft user tacos.")
class TacoWebhookMinecraftTacosPayload:
    """
    Payload that is sent to give a Minecraft user tacos.
    >>>openapi
      properties:
        guild_id:
          description: The ID of the guild where the tacos are being sent.
        from_user:
          description: The user who is sending the tacos.
        to_user_id:
          description: The ID of the user who is receiving the tacos.
        amount:
          description: The number of tacos being sent.
        reason:
          description: The reason for sending the tacos.
        type:
          description: The event type for giving the tacos to the user.
          enum:
            - login
            - custom
    <<<openapi
    """
    def __init__(self, payload: dict):
        self.guild_id: str = payload.get("guild_id", "")
        self.from_user: str = payload.get("from_user", "")
        self.to_user_id: str = payload.get("to_user_id", "")
        self.amount: int = payload.get("amount", 0)
        self.reason: str = payload.get("reason", "")
        self.type: typing.Literal['login', 'custom'] = payload.get("type", "")
