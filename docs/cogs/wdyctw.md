
# WDYCTW Cog (What Do You Call This Wednesday)

This cog manages "What Do You Call This Wednesday" (WDYCTW) events, allowing administrators to prompt users to share their weekly creations, import posts, and reward participants with tacos.

## Commands

- **wdyctw** (admin only): Main command group for WDYCTW events. Prompts the admin to submit a WDYCTW post (with image and/or text) to a configured channel, tagging a role if set.
  - **import &lt;message_id&gt;** (admin only): Import a WDYCTW post from an existing message in the output channel.
  - **give &lt;member&gt;** (admin only): Give a user tacos for their WDYCTW submission.

## Reactions

- Admins can react to WDYCTW posts with configured emojis to automatically give tacos or import posts, depending on the emoji and the day of the week.

## Listeners

- **on_raw_reaction_add**: Handles admin reactions for giving tacos or importing WDYCTW posts.

## Purpose

The `WDYCTW` cog is designed to encourage community engagement by prompting members to share their weekly creations, rewarding participation, and making it easy for admins to manage and track these events.

## Example Usage

- `.wdyctw` — Start a new WDYCTW prompt (admin only)
- `.wdyctw import <message_id>` — Import a WDYCTW post from an existing message (admin only)
- `.wdyctw give @user` — Give tacos to a user for their WDYCTW submission (admin only)
- React with the configured emoji to a WDYCTW post to give tacos or import the post (admin only)

This cog is intended for use in creative or maker communities that want to highlight and reward member projects each week.
