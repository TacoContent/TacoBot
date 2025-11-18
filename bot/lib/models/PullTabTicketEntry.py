import typing

from bot.lib import utils

# {
#   "_id": "",
#   "guild_id": "string",
#   "user_id": "string",
#   "code": "string",
#   "created_at": "number",
#   "redeemed_at": "number | null",
#   "ticket": [
#     ["string"],
#     ["string"],
#     ["string"],
#     ["string"],
#     ["string"]
#   ],
#   "reward": "number"
# }


class PullTabTicketEntry:
    def __init__(
        self,
        *,  # force keyword arguments
        guild_id: int,
        user_id: int,
        code: str,  # unique code for the ticket
        ticket: typing.List[str],  # ticket is a list of strings, each string is a line
        created_at: typing.Optional[typing.Union[int, float]] = None,
        redeemed_at: typing.Optional[typing.Union[int, float]] = None,
        reward: int = 0,
        # would be: [{"line1": amount}, {"line2": amount}, ...]
        # example: [{"🌮": 10}, {"🍉🍉🍉": 500}]
        winning_lines: typing.Optional[typing.List[typing.Dict[str, int]]] = None,
        effective_multiplier: typing.Optional[float] = 1,
        purchase_multiplier: typing.Optional[float] = 1,
        cost: typing.Optional[int] = 10,
    ) -> None:
        self.guild_id = str(guild_id)
        self.user_id = str(user_id)
        self.code = code
        if created_at is None:
            self.created_at = int(utils.get_timestamp())
        else:
            self.created_at = created_at
        self.redeemed_at = redeemed_at
        self.ticket = ticket
        self.reward = reward
        self.winning_lines = winning_lines
        if effective_multiplier is None or effective_multiplier < 1:
            self.effective_multiplier = 1
        self.effective_multiplier = effective_multiplier
        if purchase_multiplier is None or purchase_multiplier < 1:
            self.purchase_multiplier = 1
        self.purchase_multiplier = purchase_multiplier
        if cost is None or cost < 0:
            self.cost = 10
        self.cost = cost

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        # this should return a dict suitable for dumping to YAML
        # it should __dict__ recursively
        # exclude None values
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}

    @staticmethod
    def from_dict(data: typing.Dict[str, typing.Any]) -> 'PullTabTicketEntry':

        guild_id: typing.Optional[typing.Union[int, str]] = data.get("guild_id", None)
        if guild_id is None:
            raise ValueError("guild_id is required")
        if isinstance(guild_id, str):
            guild_id = int(guild_id)

        user_id: typing.Optional[typing.Union[int, str]] = data.get("user_id", None)
        if user_id is None:
            raise ValueError("user_id is required")
        if isinstance(user_id, str):
            user_id = int(user_id)

        code: typing.Optional[str] = data.get("code", None)
        if code is None:
            raise ValueError("code is required")

        ticket: typing.Optional[typing.List[str]] = data.get("ticket", None)
        if ticket is None:
            raise ValueError("ticket is required")

        return PullTabTicketEntry(
            guild_id=int(guild_id),
            user_id=int(user_id),
            code=code,
            ticket=ticket,
            created_at=data.get("created_at", None),
            redeemed_at=data.get("redeemed_at", None),
            reward=data.get("reward", 0),
            winning_lines=data.get("winning_lines", None),
            effective_multiplier=data.get("effective_multiplier", 1),
            purchase_multiplier=data.get("purchase_multiplier", 1),
            cost=data.get("cost", 10),
        )
