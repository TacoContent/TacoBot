# Events Cog

This cog handles various Discord bot events for TacoBot, providing logging and error handling for key lifecycle events.

## Listeners

- **on_ready**: Logs when the bot is ready and connected as a user.
- **on_guild_available**: Handles when a guild becomes available.
- **on_disconnect**: Logs when the bot disconnects from Discord.
- **on_resumed**: Logs when the bot session is resumed after a disconnect.
- **on_error**: Logs errors that occur during event processing, including stack traces.

## Commands

- (No public commands; event-driven only.)

## Features

- Monitors and logs the bot's connection status and errors.
- Ensures important lifecycle events are tracked for debugging and operational awareness.

## Example Usage

- (No user-facing commands; operates automatically on bot events.)
