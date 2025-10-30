# AnnouncementsCog

Tracks and persists messages from configured announcement channels in a guild. This cog centralizes logic for importing historical messages (optional) and reacting to message lifecycle events (create, edit, delete, bulk delete) so that downstream features (dashboards, analytics, APIs) can operate over a stable stored snapshot.

## Purpose

- Preserve a history of important announcement content (even after edits or deletions)
- Provide a normalized structure detached from Discord's runtime objects
- Enable future enrichment, analytics, and external display

## Settings (per guild / section: `announcements`)

| Key | Type | Description |
|-----|------|-------------|
| `enabled` | boolean | Enables the cog; if false all events are ignored. |
| `channels` | string[] | Channel IDs (as strings) to track announcements from. |
| `import_existing` | boolean | When true, performs a backfill on guild availability. |
| `import_limit` | integer | Max messages to scan per channel during backfill (default 100). |
| `last_import` | integer (epoch) | Timestamp of the last successful import (written by the cog). |

## Listeners

| Event | Behavior |
|-------|----------|
| `on_guild_available` | Optionally backfills recent messages from configured channels. |
| `on_message` | Tracks newly created messages in tracked channels. |
| `on_message_edit` | Updates stored snapshot with edited state. |
| `on_message_delete` | Marks a message as deleted (records `deleted_at`). |
| `on_bulk_message_delete` | Marks each deleted message individually. |
| `on_raw_message_delete` | Placeholder (future: handle uncached deletes). |

All message-related listeners delegate to a single internal method `_track_announcement` which centralizes filtering, logging and persistence.

## Data Flow

1. Event received from Discord gateway.
2. Cog resolves guild settings and verifies channel eligibility.
3. Builds an `AnnouncementEntry` (wrapping an `AnnouncementMessage`).
4. Persists via `AnnouncementsDatabase.track_announcement` (upsert semantics).

## Stored Fields (See `announcements` collection doc)

- Guild / channel / message identifiers
- Author ID
- Lifecycle timestamps: `created_at`, `updated_at`, optional `deleted_at`
- Snapshot of message content: text, embeds, attachments, reactions, nonce, type
- `tracked_at` persistence timestamp (separate from message times)

## Import Behavior

When `import_existing = true`, on guild availability the cog walks each configured channel history (respecting `import_limit`) and ingests messages using the same tracking path as live events to ensure consistent shaping.

## Example Configuration Snippet

```json
{
  "announcements": {
    "enabled": true,
    "channels": ["123456789012345678", "234567890123456789"],
    "import_existing": true,
    "import_limit": 150
  }
}
```

## Future Extensions

- Add filtering by minimum age or content patterns
- REST API endpoints to query stored announcements with pagination
- Webhook or feed export for external dashboards
- Enrich stored data with role / username snapshots for historical context

## Related

- Database: [announcements collection](../databases/announcements.md)
- Model Classes: `AnnouncementEntry`, `AnnouncementMessage`
