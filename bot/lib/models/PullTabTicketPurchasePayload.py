import typing

from bot.lib.models import openapi


@openapi.managed()
@openapi.component("PullTabTicketPurchasePayload", description="Payload for purchasing pull tab tickets.")
@openapi.property("multiplier", description="The multiplier for the pull tab tickets.", default=1)
@openapi.property("quantity", description="The quantity of pull tab tickets to purchase.", default=1)
class PullTabTicketPurchasePayload:
    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.multiplier: typing.Optional[int] = data.get("multiplier", 1)
        self.quantity: typing.Optional[int] = data.get("quantity", 1)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "multiplier": self.multiplier,
            "quantity": self.quantity,
        }
