# IntroductionCog

This cog manages user introductions in TacoBot, including importing introductions and handling introduction-related commands.

## Commands

- **introduction** (aliases: intro): Main command group for introductions.
  - **import** (aliases: i): Imports introductions for the guild (admin only).
  - (Other subcommands may exist; see source for details.)

## Listeners

- None (command only)

## Features

- Allows administrators to import introductions for onboarding.
- Tracks command usage for analytics.
- Integrates with MongoDB for storing and retrieving introductions.

## Example Usage

- `.introduction import` — Import introductions (admin only)

This cog is useful for communities that want to track and manage user introductions.
