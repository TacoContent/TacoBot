# track_free_game_keys

This document describes the structure of the `track_free_game_keys` collection used in TacoBot. Each document represents a tracked free game key in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **channel_id**: *(string)*  
  The Discord channel ID.
- **game_id**: *(string)*  
  The game ID.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **message_id**: *(string)*  
  The Discord message ID.
- **timestamp**: *(number)*  
  The time the key was tracked (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "channel_id": "234567890123456789",
  "game_id": "game-001",
  "guild_id": "123456789012345678",
  "message_id": "345678901234567890",
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TrackFreeGameKey",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "channel_id": { "type": "string" },
    "game_id": { "type": "string" },
    "guild_id": { "type": "string" },
    "message_id": { "type": "string" },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "channel_id", "game_id", "guild_id", "message_id", "timestamp"]
}
```
