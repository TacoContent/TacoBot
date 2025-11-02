import collections
from typing import Any


class ContextHelper:
    """Utilities for constructing lightweight context objects for tests.

    Contract:
    - Inputs: any keyword args for attributes (bot, author, guild, channel, message, invoked_subcommand, ...)
    - Output: a simple namedtuple with matching attributes
    - Error modes: none (missing fields simply won't exist)
    - Success: returned object exposes attributes passed in kwargs
    """

    def create_context(self, **kwargs: Any):
        """Create a simple context object with arbitrary attributes.

        Example:
            ctx = ContextHelper().create_context(bot=bot, author=user, guild=guild)
            assert ctx.author is user
        """
        if not kwargs:
            # Ensure at least a stable type with no attributes
            return collections.namedtuple("Context", [])()

        ctx = collections.namedtuple("Context", kwargs.keys())(*kwargs.values())
        return ctx
