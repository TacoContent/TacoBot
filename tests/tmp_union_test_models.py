"""Temporary test models for Union type and Optional[Union[...]] testing.

This module contains example models used exclusively for testing Union type
detection, oneOf/anyOf schema generation, and nullable union support.
These models should not be imported or used in production code.

NOTE: This file follows the tmp_* naming convention used in tests for
      temporary test fixtures. These models are NOT scanned during production
      swagger sync since the --models-root defaults to bot/lib/models.
"""

import typing

from bot.lib.models.DiscordRole import DiscordRole
from bot.lib.models.DiscordUser import DiscordUser
from bot.lib.models.openapi import openapi


# Test filter models for SearchCriteria union type
@openapi.component()
class SearchDateFilter:
    """Date range filter for search."""

    start_date: str
    end_date: str


@openapi.component()
class SearchAuthorFilter:
    """Author filter for search."""

    author_id: str
    author_name: str | None


@openapi.component()
class SearchTagFilter:
    """Tag filter for search."""

    tags: list[str]
    match_all: bool


# Search criteria can combine multiple filter types (anyOf)
SearchCriteria: typing.TypeAlias = typing.Union[SearchDateFilter, SearchAuthorFilter, SearchTagFilter]

openapi.type_alias(
    "SearchCriteria",
    description="Search filters that can be combined - supports date range, author, and/or tag filters.",
    anyof=True,
    managed=True,
)(typing.cast(typing.Any, SearchCriteria))


# Test 1: Optional[Union[...]] pattern - nullable discriminated union
OptionalMentionable: typing.TypeAlias = typing.Optional[typing.Union[DiscordRole, DiscordUser]]

openapi.type_alias(
    "OptionalMentionable", description="An optional Discord mentionable entity (role, user, or null).", managed=True
)(typing.cast(typing.Any, OptionalMentionable))


# Test 2: Union[A, B, C, None] pattern - nullable composable union
OptionalSearchCriteria: typing.TypeAlias = typing.Union[SearchDateFilter, SearchAuthorFilter, SearchTagFilter, None]

openapi.type_alias(
    "OptionalSearchCriteria",
    description="Optional search filters that can be combined (date, author, tags, or null).",
    anyof=True,  # Composable filters use anyOf
    managed=True,
)(typing.cast(typing.Any, OptionalSearchCriteria))


# Note: SearchCriteria, SearchDateFilter, SearchAuthorFilter, and SearchTagFilter
# were originally in bot/lib/models/SearchCriteria.py but have been moved here
# since they are test-only models created to validate Union/anyOf functionality.
