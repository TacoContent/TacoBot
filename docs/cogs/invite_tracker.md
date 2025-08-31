# InviteTracker

This cog tracks Discord invite codes, logging their creation, deletion, and usage for analytics and moderation purposes.

## Listeners

- **on_ready**: Loads and tracks all invites for each guild when the bot is ready.
- **on_invite_create**: Tracks new invite codes as they are created.
- **on_invite_delete**: Updates tracking when invites are deleted.

## Commands

- (No public commands; event-driven only.)

## Features

- Monitors and records invite code activity for analytics and moderation.
- Integrates with MongoDB for invite tracking.

## Example Usage

- (No user-facing commands; operates automatically on invite events.)
