# Collection: announcements

Stores tracked announcement messages captured from configured guild channels. Each document represents a single Discord message snapshot with lifecycle metadata and content.

## Purpose

Provide a durable, queryable record of messages from designated announcement channels, including edits and soft deletions, enabling:

- Analytics & dashboards
- Historical audits / moderation context
- External API exposure without hitting Discord directly

## Document Identity

Documents are uniquely identified by the compound key (`guild_id`, `channel_id`, `message_id`). A MongoDB index (recommended) should enforce uniqueness for those three fields; an `_id` ObjectId will still exist automatically.

## Field Summary

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Standard MongoDB primary key. |
| `guild_id` | String | Discord guild (server) ID. |
| `channel_id` | String | Discord text channel ID. |
| `message_id` | String | Discord message ID. |
| `author_id` | String | Author user ID. |
| `created_at` | Number (epoch seconds) | Original message creation time. |
| `updated_at` | Number (epoch seconds) | Last edit timestamp (or equals created_at). |
| `deleted_at` | Number or null | When message deletion observed (soft delete), null if active. |
| `tracked_at` | Number (epoch seconds) | When this snapshot was persisted/updated. |
| `message` | Object or null | Nested content snapshot (see below). |

### Nested `message` Object

| Field | Type | Notes |
|-------|------|-------|
| `content` | String | Raw textual content. |
| `embeds` | Array of Object | Raw embed dicts (`discord.Embed.to_dict()`). |
| `attachments` | Array of Object | Each element: `{ id: string, url: string }`. |
| `reactions` | Array of Object | Each element: `{ emoji: string, count: number }`. |
| `nonce` | String or Number or null | Client-provided nonce if available. |
| `type` | String | Discord message type enum name. |

## Example Document

```json
{
  "_id": "ObjectId(…)",
  "guild_id": "123456789012345678",
  "channel_id": "234567890123456789",
  "message_id": "345678901234567890",
  "author_id": "456789012345678901",
  "created_at": 1728105600,
  "updated_at": 1728105600,
  "deleted_at": null,
  "tracked_at": 1728105610,
  "message": {
    "content": "Server maintenance tomorrow at 9AM UTC.",
    "embeds": [],
    "attachments": [],
    "reactions": [ { "emoji": "✅", "count": 14 } ],
    "nonce": null,
    "type": "default"
  }
}
```

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Announcements",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId" },
    "guild_id": { "type": "string" },
    "channel_id": { "type": "string" },
    "message_id": { "type": "string" },
    "author_id": { "type": "string" },
    "created_at": { "type": "number" },
    "updated_at": { "type": "number" },
    "deleted_at": { "type": ["number", "null"] },
    "tracked_at": { "type": "number" },
    "message": {
      "type": ["object", "null"],
      "properties": {
        "content": { "type": "string" },
        "embeds": { "type": "array", "items": { "type": "object" } },
        "attachments": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "id": { "type": "string" },
              "url": { "type": "string" }
            },
            "required": ["id", "url"]
          }
        },
        "reactions": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "emoji": { "type": "string" },
              "count": { "type": "number" }
            },
            "required": ["emoji", "count"]
          }
        },
        "nonce": { "type": ["string", "number", "null"] },
        "type": { "type": "string" }
      },
      "required": ["content", "embeds", "attachments", "reactions", "nonce", "type"]
    }
  },
  "required": ["_id", "guild_id", "channel_id", "message_id", "author_id", "created_at", "updated_at", "deleted_at", "tracked_at", "message"]
}
```

## Index Recommendations

- Compound unique index: `(guild_id, channel_id, message_id)`
- Optional TTL index on `deleted_at` if you plan to purge hard-deleted messages after N days (only if not needed historically).

## Related

- Cog: [AnnouncementsCog](../cogs/announcements.md)
- Source: `bot/cogs/announcements.py`
- Model: `bot/lib/models/AnnouncementEntry.py`
