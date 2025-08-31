# GameKeysCog

This cog manages game key rewards, offers, and related interactions in TacoBot. It integrates with databases, permissions, and external APIs to facilitate game key distribution and tracking.

## Commands

- (Commands for offering, claiming, and managing game keys; see source for details.)

## Listeners

- **on_ready**: Loads cog settings and checks for open game key offers when the bot is ready.

## Features

- Allows administrators to offer and manage game key rewards.
- Integrates with MongoDB and Steam API for key management.
- Tracks command usage for analytics.

## Example Usage

- `.gamekeys offer` — Offer a new game key (if implemented)
- `.gamekeys claim` — Claim a game key (if implemented)

This cog is intended for use in communities that distribute game keys as rewards or giveaways. It is tightly integrated with TacoBot's database and permission systems.
