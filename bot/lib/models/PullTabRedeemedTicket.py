
import typing

from bot.lib.models import openapi
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry


@openapi.managed()
@openapi.component("PullTabRedeemedTicket", description="Result of a redeemed pull-tab ticket.")
@openapi.property("success", description="Indicates if the ticket redemption was successful.", default=False)
@openapi.property("reward", description="The reward amount from the redeemed ticket.", default=0)
@openapi.property("message", description="A message related to the ticket redemption.", default="")
@openapi.property("ticket", description="The details of the redeemed pull-tab ticket.", default=None)
class PullTabRedeemedTicket:
    def __init__(
        self,
        *,
        success: bool = False,
        reward: int = 0,
        message: str = "",
        ticket: typing.Optional[PullTabTicketEntry] = None
    ) -> None:

        self.success: bool = success
        self.reward: int = reward
        self.message: str = message
        self.ticket: typing.Optional[PullTabTicketEntry] = ticket

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "success": self.success,
            "reward": self.reward,
            "message": self.message,
            "ticket": self.ticket.to_dict() if self.ticket else None,
        }

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "PullTabRedeemedTicket":
        ticket_data = data.get("ticket")
        ticket = PullTabTicketEntry.from_dict(ticket_data) if isinstance(ticket_data, dict) else None

        return cls(
            success=data.get("success", False),
            reward=data.get("reward", 0),
            message=data.get("message", ""),
            ticket=ticket,
        )
