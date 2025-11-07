import typing


class UserInviteSystemActionData:
    def __init__(self, data: typing.Dict[str, typing.Any]) -> None:
        self.inviter_id = data.get("inviter_id", "")
        self.inviter_name = data.get("inviter_name", "")
        self.invited_id = data.get("invited_id", "")
        self.invited_name = data.get("invited_name", "")
        self.invite_code = data.get("invite_code", "")

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        # this should return a dict suitable for dumping to YAML
        # it should __dict__ recursively
        # exclude None values
        return {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.__dict__.items() if v is not None}
