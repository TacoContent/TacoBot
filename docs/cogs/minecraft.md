# MinecraftCog

This cog provides commands and event listeners for managing a Minecraft server through TacoBot, including server status, start/stop controls, and user whitelisting.

## Commands

- **minecraft**: Main command group for Minecraft server management.
  - **status**: Shows the current status of the Minecraft server, including host, player slots, version, mods, and whether the server is online or offline.
  - **start**: Starts the Minecraft server. Only available to whitelisted users. Notifies the user if the server is already running.
  - **stop**: Stops the Minecraft server. Requires administrator permissions. Notifies the user if the server is already stopped.
  - **whitelist**: Guides a user through the process of adding themselves to the Minecraft server whitelist, including username verification and avatar confirmation.
  - (Other subcommands may exist; see source for details.)

## Listeners

- **on_member_remove**: Automatically removes a user from the Minecraft whitelist if they leave the Discord server.

## Features

- Allows users to check server status, start/stop the server, and manage the whitelist.
- Integrates with external APIs and MongoDB for server and user management.
- Tracks command usage for analytics.

## Example Usage

- `.taco minecraft status` — View server status
- `.taco minecraft start` — Start the server (if whitelisted)
- `.taco minecraft stop` — Stop the server (admin only)
- `.taco minecraft whitelist` — Add yourself to the whitelist

This cog is intended for use in Discord servers that host a Minecraft community and want to automate server management tasks.
