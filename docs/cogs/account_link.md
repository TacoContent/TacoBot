# AccountLink Cog

This cog handles linking a user's Twitch account to their Discord account. Provides both slash and text commands for requesting and verifying a link code.

## Commands

- `/link request` — Request a code to link your Twitch account to Discord. The bot will DM you a code.
- `/link verify <code>` — Verify your Twitch account by entering the code you received from the bot.
- `!link [code]` — If a code is provided, attempts to link your Twitch account. If no code is provided, generates and DMs a new code.

## Listeners

- None (command only)

## Features

- Tracks command usage and system actions for analytics.
- Handles errors and notifies users via DM or channel message.
- Integrates with MongoDB for storing link codes and tracking actions.

## Example Usage

- `/link request`
- `/link verify ABC123`
- `!link ABC123`

This cog implements account linking, code generation, verification, and error handling for Discord/Twitch integration.
