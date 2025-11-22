import typing


class PullTabTicketPurchasePayload:
    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.multiplier: typing.Optional[int] = data.get("multiplier", 1)
        self.quantity: typing.Optional[int] = data.get("quantity", 1)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "multiplier": self.multiplier,
            "quantity": self.quantity,
        }
