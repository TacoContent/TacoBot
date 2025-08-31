# Giphy Cog

This cog provides a command to search and post GIFs from Giphy in Discord channels.

## Commands

- **giphy** (aliases: gif): Searches Giphy for a GIF matching the provided query and posts a random result in the channel. Usage: `.giphy <search term>` or `.gif <search term>`. Restricted to guild use only.

## Listeners

- None (command only)

## Features

- Integrates with the Giphy API to fetch GIFs.
- Randomizes results and posts a rich embed with the GIF.
- Deletes the user's command message for a cleaner chat experience.
- Tracks command usage for analytics.

## Example Usage

- `.giphy tacos` — Posts a random taco-related GIF
- `.gif cats` — Posts a random cat GIF

This cog is useful for adding fun and interactivity to your Discord server.
