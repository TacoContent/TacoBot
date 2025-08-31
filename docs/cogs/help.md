# HelpCog

This cog provides help and changelog commands for TacoBot, allowing users to view recent changes and get help information.

## Commands

- **changelog** (aliases: changes, cl): Displays the changelog for TacoBot, chunked into pages if necessary.
- **help**: (If implemented) Shows help information for available commands.

## Listeners

- None (command only)

## Features

- Reads and parses the changelog file, splitting it into versions and paginating if needed.
- Deletes the user's command message for a cleaner chat experience.
- Tracks command usage for analytics.

## Example Usage

- `.changelog` — View the bot's changelog
- `.help` — Show help information (if implemented)

This cog is useful for keeping users up to date with the latest changes and available commands.
