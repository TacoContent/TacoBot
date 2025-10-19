
import typing

from lib.models.openapi import openapi

@openapi.component("GuildItemIdBatchRequestBody", description="Request body for batch fetching guild item by IDs")
@openapi.managed()
class GuildItemIdBatchRequestBody:
    def __init__(self, data: typing.Dict[str, typing.Any]):
        self.ids: typing.List[str] = [str(id) for id in data.get("ids", [])]

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {"ids": self.ids}


@openapi.component("GuildChannelsBatchRequestBody", description="Request body for batch fetching guild channels by IDs")
@openapi.exclude()
class GuildChannelsBatchRequestBody:
    pass  # Placeholder for the original class to be ignored in this context
