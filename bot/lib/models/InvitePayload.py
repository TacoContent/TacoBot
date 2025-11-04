import typing


class InvitePayload:

    def __init__(self, data: typing.Dict[str, typing.Any]) -> None:
        self.id = data.get("id", "")
        self.code = data.get("code", "")
        self.inviter_id = data.get("inviter_id", "")
        self.uses = data.get("uses", 0)
        self.max_uses = data.get("max_uses", 0)
        self.max_age = data.get("max_age", 0)
        self.temporary = data.get("temporary", False)
        self.created_at = data.get("created_at", 0)
        self.revoked = data.get("revoked", False)
        self.channel_id = data.get("channel_id", "")
        self.url = data.get("url", "")

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        # this should return a dict suitable for dumping to YAML
        # it should __dict__ recursively
        # exclude None values
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}
