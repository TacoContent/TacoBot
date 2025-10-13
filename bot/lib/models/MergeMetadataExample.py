"""Example model demonstrating merged metadata from legacy and unified blocks."""

import typing
from bot.lib.models.openapi import openapi_model


@openapi_model("MergeMetadataExample", description="Demonstrates metadata merging order.")
class MergeMetadataExample:
    """Demonstrates merging rules.

    >>>openapi
    properties:
      literal:
        description: A literal field
        enum: [simple]
      primary:
        description: Primary description from legacy block
      merged:
        enum: [a, b, c]
        description: description (should persist)
      added_only_in_unified:
        description: Provided only by unified block
    <<<openapi
    """
    def __init__(self):
        self.literal: typing.Literal["example"] = "example"
        self.primary: str = "p"
        self.merged: str = "m"
        self.added_only_in_unified: str = "u"
