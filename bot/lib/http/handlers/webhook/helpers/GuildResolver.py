"""Guild and channel resolution for webhook broadcasting."""

from dataclasses import dataclass
from typing import Callable, List, Optional

import discord
from bot.lib import discordhelper
from bot.lib.mongodb.free_game_keys import FreeGameKeysDatabase


@dataclass
class ResolvedGuild:
    """Guild with resolved notification channels."""

    guild_id: int
    channels: List[discord.TextChannel]
    notify_role_ids: List[int]


class GuildResolver:
    """Resolve eligible guilds and channels for offer broadcasting."""

    def __init__(
        self,
        get_settings_func: Callable[[int, str], dict],
        freegame_db: FreeGameKeysDatabase,
        discord_helper: discordhelper.DiscordHelper,
    ):
        self.get_settings: Callable[[int, str], dict] = get_settings_func
        self.freegame_db: FreeGameKeysDatabase = freegame_db
        self.discord_helper: discordhelper.DiscordHelper = discord_helper

    async def resolve_eligible_guilds(
        self, guilds: List[discord.Guild], game_id: int, settings_section: str
    ) -> List[ResolvedGuild]:
        """Filter guilds and resolve notification channels.

        Args:
            guilds: All bot guilds
            game_id: Unique game identifier for deduplication
            settings_section: Settings section name (e.g., "free_games")

        Returns:
            List of guilds with resolved channels and role IDs
        """
        resolved = []

        for guild in guilds:
            guild_config = self._get_guild_config(guild.id, game_id, settings_section)

            if not guild_config:
                continue  # Guild disabled or already tracked

            channels = await self._resolve_channels(guild_config['channel_ids'])

            if not channels:
                self._log_no_channels(guild.id)
                continue

            resolved.append(
                ResolvedGuild(guild_id=guild.id, channels=channels, notify_role_ids=guild_config['notify_role_ids'])
            )

        return resolved

    def _get_guild_config(self, guild_id: int, game_id: int, settings_section: str) -> Optional[dict]:
        """Get guild config if eligible for notification.

        Returns None if guild is ineligible.
        """
        settings = self.get_settings(guild_id, settings_section)

        if not settings.get("enabled", False):
            return None

        if self.freegame_db.is_game_tracked(guild_id, game_id):
            return None

        channel_ids = settings.get("channel_ids", [])
        if not channel_ids:
            return None

        return {'channel_ids': channel_ids, 'notify_role_ids': settings.get("notify_role_ids", [])}

    async def _resolve_channels(self, channel_ids: List[int]) -> List[discord.TextChannel]:
        """Resolve channel IDs to channel objects."""

        channels = []
        for channel_id in channel_ids:
            channel = await self.discord_helper.get_or_fetch_channel(int(channel_id))
            if channel:
                channels.append(channel)
        return channels

    def _log_no_channels(self, guild_id: int):
        """Log when no valid channels found."""
        # Inject logger if needed
        pass
