# introductions

This document describes the structure of the `introductions` collection used in TacoBot. Each document represents a user introduction in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **user_id**: *(string)*  
  The Discord user ID.
- **approved**: *(boolean)*  
  Whether the introduction was approved.
- **channel_id**: *(string)*  
  The Discord channel ID.
- **message_id**: *(string)*  
  The Discord message ID.
- **timestamp**: *(number)*  
  The time the introduction was posted (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "user_id": "987654321098765432",
  "approved": true,
  "channel_id": "234567890123456789",
  "message_id": "345678901234567890",
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Introduction",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "user_id": { "type": "string" },
    "approved": { "type": "boolean" },
    "channel_id": { "type": "string" },
    "message_id": { "type": "string" },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "guild_id", "user_id", "approved", "channel_id", "message_id", "timestamp"]
}
```
