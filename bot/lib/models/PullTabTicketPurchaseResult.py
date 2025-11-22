
import typing

from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry


class PullTabTicketPurchaseResult:
    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.total_cost: float = data.get("total_cost", 0.0)
        self.tickets: typing.List[PullTabTicketEntry] = [
            PullTabTicketEntry.from_dict(ticket) if isinstance(ticket, dict) else ticket
            for ticket in data.get("tickets", [])
        ]
        self.remaining_balance: float = data.get("remaining_balance", 0.0)
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
