"""Test models for union type handling and oneOf schema generation.

These models are used by tests in test_swagger_sync_union_oneof.py
to verify union type detection and schema generation.
"""

import typing
from typing import Optional, Union

from bot.lib.models import DiscordRole, DiscordUser
from bot.lib.models.openapi import openapi

# Test model for Optional[Union[...]] with nullable: true
OptionalMentionable: typing.TypeAlias = Optional[Union[DiscordRole, DiscordUser]]  # type: ignore

# Apply decorators to make it discoverable
openapi.type_alias(
    "OptionalMentionable", description="An optional Discord mentionable entity (role, user, or null).", managed=True
)(OptionalMentionable)


# Test models for SearchCriteria with anyof=True
class SearchDateFilter:
    """Filter by date range."""

    start_date: str
    end_date: str


class SearchAuthorFilter:
    """Filter by author."""

    author_id: str


class SearchTagFilter:
    """Filter by tags."""

    tags: list[str]


# Union with anyof=True for composable filters
SearchCriteria: typing.TypeAlias = Union[SearchDateFilter, SearchAuthorFilter, SearchTagFilter]

openapi.type_alias(
    "SearchCriteria",
    description="Search filters that can be combined - supports date range, author, and/or tag filters.",
    managed=True,
    anyof=True,  # This should generate anyOf instead of oneOf
)(SearchCriteria)


# Test for Union[..., None] with anyof=True and nullable: true
OptionalSearchCriteria: typing.TypeAlias = Union[SearchDateFilter, SearchAuthorFilter, SearchTagFilter, None]

openapi.type_alias(
    "OptionalSearchCriteria",
    description="Optional search filters that can be combined or omitted.",
    managed=True,
    anyof=True,
)(OptionalSearchCriteria)
