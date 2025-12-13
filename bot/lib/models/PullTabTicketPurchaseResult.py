
import typing

from bot.lib.models import openapi
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry


@openapi.managed()
@openapi.component("PullTabTicketPurchaseResult", description="Result of a pull-tab ticket purchase.")
@openapi.property("total_cost", description="The total cost of the purchased tickets.", default=0)
@openapi.property("tickets", description="List of purchased pull tab tickets.", default=[])
@openapi.property("remaining_balance", description="The remaining balance after purchase.", default=0)
@openapi.property("success", description="Indicates if the purchase was successful.", default=False)
@openapi.property("user_id", description="ID of the user who made the purchase.", default=0)
@openapi.property("guild_id", description="ID of the guild where the purchase was made.", default=0)
class PullTabTicketPurchaseResult:
    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.total_cost: int = data.get("total_cost", 0)
        self.tickets: typing.List[PullTabTicketEntry] = [
            PullTabTicketEntry.from_dict(ticket) if isinstance(ticket, dict) else ticket
            for ticket in data.get("tickets", [])
        ]
        self.remaining_balance: int = data.get("remaining_balance", 0)
        self.success: bool = data.get("success", False)
        self.user_id: int = data.get("user_id", 0)
        self.guild_id: int = data.get("guild_id", 0)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "total_cost": self.total_cost,
            "tickets": [ticket.to_dict() for ticket in self.tickets],
            "remaining_balance": self.remaining_balance,
            "success": self.success,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
        }
