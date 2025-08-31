# live_tracked

This document describes the structure of the `live_tracked` collection used in TacoBot. Each document represents a tracked live event or stream in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **platform**: *(string)*  
  The platform (e.g., "Twitch").
- **user_id**: *(string)*  
  The Discord user ID.
- **channel_id**: *(string)*  
  The Discord channel ID.
- **message_id**: *(string)*  
  The Discord message ID.
- **timestamp**: *(number)*  
  The time the event was tracked (epoch).
- **url**: *(string)*  
  The URL of the live event or stream.

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "platform": "Twitch",
  "user_id": "987654321098765432",
  "channel_id": "234567890123456789",
  "message_id": "345678901234567890",
  "timestamp": 1693459200,
  "url": "https://twitch.tv/streamer"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LiveTracked",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "platform": { "type": "string" },
    "user_id": { "type": "string" },
    "channel_id": { "type": "string" },
    "message_id": { "type": "string" },
    "timestamp": { "type": "number" },
    "url": { "type": "string" }
  },
  "required": ["_id", "guild_id", "platform", "user_id", "channel_id", "message_id", "timestamp", "url"]
}
```
