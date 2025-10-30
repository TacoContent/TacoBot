"""Model representing a Minecraft whitelist (and optional op) entry.

This lightweight data container mirrors a record stored or derived from
guild-scoped Minecraft server management state. It intentionally keeps a
flat structure for easy JSON (de)serialization.

Fields
------
user_id : int
    Internal or Discord-linked user identifier (0 if unknown/unset).
guild_id : int
    Discord guild id to scope ownership of this whitelist record.
username : str
    Minecraft username (case-insensitive uniqueness typically enforced upstream).
uuid : str
    Mojang / Microsoft account UUID (hyphenated or raw). Empty when not resolved yet.
whitelist : bool
    Whether the user is currently whitelisted.
op : bool | None
    Operator status flag (``True`` if op, ``False`` if explicitly not an op,
    ``None`` if unknown or not yet computed / synchronized).

Design Notes
------------
* No validation is performed here—callers are responsible for ensuring
    username/uuid consistency.
* ``*args`` are accepted for forward compatibility but ignored; only
    keyword arguments are used to populate attributes.
* Consider promoting to a ``dataclass`` if immutability or type-based
    tooling becomes desirable in future refactors.
"""


class MinecraftWhitelistUser:
    """Container for guild-scoped Minecraft whitelist state.

    Parameters
    ----------
    *args
        Ignored positional arguments (accepted for lenient construction).
    **kwargs
        Attribute overrides (see module docstring fields list).
    """

    def __init__(self, *args, **kwargs):
        # set properties from kwargs
        self.user_id = kwargs.get("user_id", 0)
        self.guild_id = kwargs.get("guild_id", 0)
        self.username = kwargs.get("username", "")
        self.uuid = kwargs.get("uuid", "")
        self.whitelist = kwargs.get("whitelist", False)
        self.op = kwargs.get("op", None)
