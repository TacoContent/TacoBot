import typing

from lib.models.openapi import openapi


@openapi.component("GuildItemIdBatchRequestBody", description="Request body for batch fetching guild item by IDs")
@openapi.property("ids", description="List of guild item IDs to fetch")
@openapi.managed()
class GuildItemIdBatchRequestBody:
    def __init__(self, data: typing.Dict[str, typing.Any]):
        if data is None:
            data = {}

        self.ids: typing.List[str] = (
            [str(id) for id in data.get("ids", [])] if isinstance(data.get("ids", []), list) else []
        )

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {"ids": self.ids}

@openapi.component("GuildItemNameBatchRequestBody", description="Request body for batch fetching guild item by names")
@openapi.property("names", description="List of guild item names to fetch")
@openapi.managed()
class GuildItemNameBatchRequestBody:
    def __init__(self, data: typing.Dict[str, typing.Any]):
        if data is None:
            data = {}

        self.names: typing.List[str] = (
            [str(name) for name in data.get("names", [])] if isinstance(data.get("names", []), list) else []
        )

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {"names": self.names}
