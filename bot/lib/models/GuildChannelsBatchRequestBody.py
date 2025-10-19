
import typing

from lib.models.openapi import openapi

@openapi.component("GuildChannelsBatchRequestBody", description="Request body for batch fetching guild channels by IDs")
@openapi.managed()
class GuildChannelsBatchRequestBody:
    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.ids: typing.List[str] = [str(id) for id in data.get("ids", [])]

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {"ids": self.ids}
