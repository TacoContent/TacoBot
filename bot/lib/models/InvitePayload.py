import typing

import discord


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


class InvitePayloadFactory:

    def __init__(self) -> None:
        pass

    def create_from_dict(self, data: typing.Dict[str, typing.Any]) -> InvitePayload:
        return InvitePayload(data)

    def create_from_invite(self, invite: discord.Invite) -> InvitePayload:
        return InvitePayload(
            {
                "id": invite.id,
                "code": invite.code,
                "inviter_id": str(invite.inviter.id) if invite.inviter else "",
                "uses": invite.uses if invite.uses is not None else 0,
                "max_uses": invite.max_uses if invite.max_uses is not None else 0,
                "max_age": invite.max_age if invite.max_age is not None else 0,
                "temporary": invite.temporary if invite.temporary is not None else False,
                "created_at": invite.created_at,
                "revoked": invite.revoked if invite.revoked is not None else False,
                "channel_id": str(invite.channel.id) if invite.channel else "",
                "url": invite.url,
            }
        )
