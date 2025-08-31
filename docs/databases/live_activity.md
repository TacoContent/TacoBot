# live_activity

This document describes the structure of the `live_activity` collection used in TacoBot. Each document represents a user's live activity status in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **user_id**: *(string)*  
  The Discord user ID.
- **status**: *(string)*  
  The user's live status (e.g., "online", "streaming").
- **platform**: *(string)*  
  The platform (e.g., "Twitch").
- **timestamp**: *(number)*  
  The time the activity was recorded (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "user_id": "987654321098765432",
  "status": "streaming",
  "platform": "Twitch",
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LiveActivity",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "user_id": { "type": "string", "description": "Discord user ID" },
    "status": { "type": "string", "description": "Live status" },
    "platform": { "type": "string", "description": "Platform" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" }
  },
  "required": ["_id", "guild_id", "user_id", "status", "platform", "timestamp"]
}
```
