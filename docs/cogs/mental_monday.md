# Mental Mondays Cog

This cog manages "Mental Monday" events and commands, supporting mental health discussions and activities in the Discord server.

## Commands

- **mentalmondays**: Main command group (admin only)
  - **openai** (aliases: ai): Generate a question using AI for Mental Mondays.
  - **import**: Import a Mental Monday post from an existing message ID.
  - **give**: Grant Mental Monday tacos to a member.

## Listeners

- **on_raw_reaction_add**: Handles reactions for giving tacos or importing posts, restricted to admins and specific emojis.

## Features

- Prompts admins to collect Mental Monday submissions (text/image).
- AI-powered question generation for Mental Mondays.
- Admins can import or reward posts.
- Tracks command usage and integrates with MongoDB.

## Example Usage

- `.mentalmondays` — Start or manage a Mental Monday event (admin only)
- `.mentalmondays openai` — Generate a Mental Monday question using AI
- `.mentalmondays import <message_id>` — Import a post by message ID
- `.mentalmondays give @member` — Grant tacos to a member

This cog is useful for communities that want to promote mental health awareness and engagement.
