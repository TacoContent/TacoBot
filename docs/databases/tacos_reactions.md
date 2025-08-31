# tacos_reactions

This document describes the structure of the `tacos_reactions` collection used in TacoBot. Each document represents a taco reaction event in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **timestamp**: *(number)*  
  The time the reaction was recorded (epoch).
- **user_id**: *(string)*  
  The Discord user ID.
- **channel_id**: *(string)*  
  The Discord channel ID.
- **message_id**: *(string)*  
  The Discord message ID.

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "timestamp": 1693459200,
  "user_id": "987654321098765432",
  "channel_id": "234567890123456789",
  "message_id": "345678901234567890"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TacosReaction",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "timestamp": { "type": "number" },
    "user_id": { "type": "string" },
    "channel_id": { "type": "string" },
    "message_id": { "type": "string" }
  },
  "required": ["_id", "guild_id", "timestamp", "user_id", "channel_id", "message_id"]
}
```
