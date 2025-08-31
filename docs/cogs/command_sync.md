# CommandSyncCog

This cog provides commands for synchronizing Discord application (slash) commands between the bot and Discord servers. Intended for administrators.

## Commands

- `!command sync [~|*|^]` — Syncs slash commands for the current guild or globally.
  - `~` — Syncs commands to the current guild only.
  - `*` — Copies global commands to the current guild and syncs.
  - `^` — Clears all commands from the current guild.
- Aliases: `!c sync`, `!commands sync`

## Listeners

- None (command only)

## Features

- Allows administrators to manage and sync slash commands.
- Supports granular control over command registration.
- Provides feedback and error handling in Discord.
- Tracks command usage for analytics.

## Example Usage

- `!command sync ~`
- `!c sync *`
- `!commands sync ^`

This cog is intended for bot administrators who need to manage Discord application commands.
