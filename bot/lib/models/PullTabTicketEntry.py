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
        winning_lines: typing.Optional[typing.List[str]] = None,
        winning_line_indexes: typing.Optional[typing.List[int]] = None,
        multiplier: typing.Optional[float] = 1,
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
        self.winning_line_indexes = winning_line_indexes
        if multiplier is None or multiplier < 1:
            self.multiplier = 1
        self.multiplier = multiplier

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
            winning_line_indexes=data.get("winning_line_indexes", None),
            multiplier=data.get("multiplier", 1),
        )
