# wdyctw

This document describes the structure of the `wdyctw` collection used in TacoBot. Each document represents a What Did You Code This Week event or message in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **timestamp**: *(number)*  
  The time the event/message was created (epoch).
- **answered**: *(array of objects)*  
  List of users who answered, each with:
  - **user_id**: *(string)*
  - **message_id**: *(string|null)*
  - **timestamp**: *(number)*
- **author**: *(string)*  
  The author of the message/event.
- **image**: *(string)*  
  URL or path to an image.
- **message**: *(string)*  
  The message content.
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
  "answered": [
    {"user_id": "987654321098765432", "message_id": "345678901234567890", "timestamp": 1693459300}
  ],
  "author": "TacoBot",
  "image": "https://...",
  "message": "What did you code this week?",
  "channel_id": "234567890123456789",
  "message_id": "345678901234567890"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "WDYCTW",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "timestamp": { "type": "number" },
    "answered": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "user_id": { "type": "string" },
          "message_id": { "type": ["string", "null"] },
          "timestamp": { "type": "number" }
        },
        "required": ["user_id", "message_id", "timestamp"]
      }
    },
    "author": { "type": "string" },
    "image": { "type": "string" },
    "message": { "type": "string" },
    "channel_id": { "type": "string" },
    "message_id": { "type": "string" }
  },
  "required": ["_id", "guild_id", "timestamp"]
}
```
