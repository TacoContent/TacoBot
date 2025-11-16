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
