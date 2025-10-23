from typing import TypeVar, Generic
import typing

from bot.lib.models.JoinWhitelistUser import JoinWhitelistUser
from bot.lib.models.openapi import openapi

T = TypeVar('T')

@openapi.component("PagedResults", description="Generic paginated results container.")
@openapi.property("total", description="Total number of matching items (unpaged)", default=0)
@openapi.property("skip", description="Number of items skipped (offset)", default=0, minimum=0)
@openapi.property("take", description="Requested page size", default=0, minimum=0)
@openapi.property("items", description="Page slice of items")
@openapi.managed()
class PagedResults(Generic[T]):
    """
    Represents a generic paginated set of results.
    """
    def __init__(self, data: dict):
        self.total: int = data.get("total", 0)
        self.skip: int = data.get("skip", 0)
        self.take: int = data.get("take", 0)
        self.items: typing.List[T] = data.get("items", [])

    def to_dict(self) -> dict:
        return self.__dict__

@openapi.component("PagedResultsJoinWhitelistUser", description="Generic paginated results container.")
@openapi.property("items", description="Page slice of JoinWhitelistUser items")
@openapi.managed()
class PagedResultsJoinWhitelistUser(PagedResults):
    def __init__(self, data: dict):
        super().__init__(data)
        self.items: typing.List[JoinWhitelistUser] = data.get("items", [])
