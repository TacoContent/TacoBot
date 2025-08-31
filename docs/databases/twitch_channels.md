# twitch_channels

This document describes the structure of the `twitch_channels` collection used in TacoBot. Each document represents a Twitch channel associated with a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **channel**: *(string)*  
  The Twitch channel name or ID.
- **timestamp**: *(number)*  
  The time the channel was added (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "channel": "Streamer123",
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TwitchChannel",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "channel": { "type": "string", "description": "Twitch channel name or ID" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" }
  },
  "required": ["_id", "guild_id", "channel", "timestamp"]
}
```
