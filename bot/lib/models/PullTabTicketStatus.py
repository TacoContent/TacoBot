
import typing

from lib.models.PullTabTicketEntry import PullTabTicketEntry

from bot.lib.models import openapi


@openapi.managed()
@openapi.component("PullTabTicketStatus", description="Represents the status of a pull tab ticket.")
@openapi.property("is_winner", description="Indicates if the ticket is a winning ticket.")
@openapi.property("is_redeemed", description="Indicates if the ticket has been redeemed.")
@openapi.property("ticket", description="The pull tab ticket entry details.")
class PullTabTicketStatus:
    """Represents the status of a pull tab ticket."""

    def __init__(
        self,
        ticket: PullTabTicketEntry,
    ) -> None:
        self.is_redeemed: bool = ticket.redeemed_at is not None
        self.is_winner: bool = ticket.reward is not None and ticket.reward > 0
        self.ticket: PullTabTicketEntry = ticket

    def to_dict(self):
        return {
            "is_winner": self.is_winner,
            "is_redeemed": self.is_redeemed,
            "ticket": self.ticket.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> "PullTabTicketStatus":
        return cls(
            ticket=PullTabTicketEntry.from_dict(data)
        )

    @classmethod
    def from_ticket(cls, ticket: PullTabTicketEntry) -> "PullTabTicketStatus":
        return PullTabTicketStatus(ticket=ticket)
