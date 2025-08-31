# JoinLeaveTracker

This cog tracks when members join or leave the Discord server, updating taco counts and logging events for analytics and moderation.

## Listeners

- **on_member_remove**: Removes all tacos from a user and logs the event when they leave the server.
- **on_member_join**: Handles logic for when a user joins the server (e.g., tracking, analytics, or welcome actions).

## Commands

- (No public commands; event-driven only.)

## Features

- Tracks join and leave events for analytics and moderation.
- Updates taco counts and logs actions in the database.

## Example Usage

- (No user-facing commands; operates automatically on member join/leave.)
