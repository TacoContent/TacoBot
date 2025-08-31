# stream_team_requests

This document describes the structure of the `stream_team_requests` collection used in TacoBot. Each document represents a user's request to join a stream team in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **user_id**: *(string)*  
  The Discord user ID.
- **twitch_name**: *(string)*  
  The user's Twitch name.
- **timestamp**: *(number)*  
  The time the request was made (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "user_id": "987654321098765432",
  "twitch_name": "Streamer123",
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "StreamTeamRequest",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "user_id": { "type": "string", "description": "Discord user ID" },
    "twitch_name": { "type": "string", "description": "Twitch name" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" }
  },
  "required": ["_id", "guild_id", "user_id", "twitch_name", "timestamp"]
}
```
