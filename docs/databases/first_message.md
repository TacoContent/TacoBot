# first_message

This document describes the structure of the `first_message` collection used in TacoBot. Each document in this collection represents the first message sent by a user in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **timestamp**: *(number)*  
  The time the message was sent (epoch).
- **channel_id**: *(string)*  
  The Discord channel ID.
- **message_id**: *(string)*  
  The Discord message ID.
- **user_id**: *(string)*  
  The Discord user ID.

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "timestamp": 1693459200,
  "channel_id": "234567890123456789",
  "message_id": "345678901234567890",
  "user_id": "987654321098765432"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FirstMessage",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" },
    "channel_id": { "type": "string", "description": "Discord channel ID" },
    "message_id": { "type": "string", "description": "Discord message ID" },
    "user_id": { "type": "string", "description": "Discord user ID" }
  },
  "required": ["_id", "guild_id", "timestamp", "channel_id", "message_id", "user_id"]
}
```
