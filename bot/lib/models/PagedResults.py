from typing import TypeVar, Generic
import typing

from bot.lib.models.JoinWhitelistUser import JoinWhitelistUser
from bot.lib.models.openapi import openapi

T = TypeVar('T')

@openapi.component("PagedResults", description="Generic paginated results container.")
@openapi.openapi_managed()
class PagedResults(Generic[T]):
    """
    Represents a generic paginated set of results.

    >>>openapi
    properties:
      total:
        description: Total number of matching items (unpaged)
      skip:
        description: Number of items skipped (offset)
      take:
        description: Requested page size
      items:
        description: Page slice of items
    <<<openapi
    """
    def __init__(self, data: dict):
        self.total: int = data.get("total", 0)
        self.skip: int = data.get("skip", 0)
        self.take: int = data.get("take", 0)
        self.items: typing.List[T] = data.get("items", [])

    def to_dict(self) -> dict:
        return self.__dict__

@openapi.component("PagedResultsJoinWhitelistUser", description="Generic paginated results container.")
@openapi.openapi_managed()
class PagedResultsJoinWhitelistUser(PagedResults):
    def __init__(self, data: dict):
        super().__init__(data)
        self.items: typing.List[JoinWhitelistUser] = data.get("items", [])
