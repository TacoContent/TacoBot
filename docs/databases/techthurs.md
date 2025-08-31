# techthurs

This document describes the structure of the `techthurs` collection used in TacoBot. Each document represents a Tech Thursday event or message in a Discord guild.

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
  - **message_id**: *(string)*
  - **timestamp**: *(number)*
- **author**: *(string)*  
  The author of the message/event.
- **channel_id**: *(string)*  
  The Discord channel ID.
- **image**: *(string|null)*  
  URL or path to an image, or null.
- **message**: *(string)*  
  The message content.
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
  "channel_id": "234567890123456789",
  "image": null,
  "message": "What tech are you excited about?",
  "message_id": "345678901234567890"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TechThurs",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" },
    "answered": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "user_id": { "type": "string" },
          "message_id": { "type": "string" },
          "timestamp": { "type": "number" }
        },
        "required": ["user_id", "message_id", "timestamp"]
      }
    },
    "author": { "type": "string" },
    "channel_id": { "type": "string" },
    "image": { "type": ["string", "null"] },
    "message": { "type": "string" },
    "message_id": { "type": "string" }
  },
  "required": ["_id", "guild_id", "timestamp"]
}
```
