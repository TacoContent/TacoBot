import typing


class PullTabTicket:
    def __init__(self, code: str, ticket: typing.List[typing.List[str]]):
        self.code = code
        self.ticket = ticket
        self.redeemed = None


class ProcessedPullTabTicket(PullTabTicket):
    def __init__(self, code: str, ticket: typing.List[typing.List[str]], reward: int):
        super().__init__(code, ticket)
        self.reward = reward

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
        guild_id: int,
        user_id: int,
        code: str,
        created_at: int,
        ticket: typing.List[typing.List[str]],
        redeemed_at: typing.Optional[int] = None,
        reward: int = 0,
        _id: typing.Optional[str] = None,
    ) -> None:
        self._id = _id
        self.guild_id = guild_id
        self.user_id = user_id
        self.code = code
        self.created_at = created_at
        self.redeemed_at = redeemed_at
        self.ticket = ticket
        self.reward = reward
