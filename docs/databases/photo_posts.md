# photo_posts

This document describes the structure of the `photo_posts` collection used in TacoBot. Each document represents a photo post in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **user_id**: *(string)*  
  The Discord user ID.
- **channel_id**: *(string)*  
  The Discord channel ID.
- **channel_name**: *(string)*  
  The Discord channel name.
- **message_id**: *(string)*  
  The Discord message ID.
- **message**: *(string)*  
  The message content.
- **image**: *(string)*  
  The image URL.
- **timestamp**: *(number)*  
  The time the photo was posted (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "user_id": "987654321098765432",
  "channel_id": "234567890123456789",
  "channel_name": "photos",
  "message_id": "345678901234567890",
  "message": "Check out this photo!",
  "image": "https://...",
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PhotoPost",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "user_id": { "type": "string" },
    "channel_id": { "type": "string" },
    "channel_name": { "type": "string" },
    "message_id": { "type": "string" },
    "message": { "type": "string" },
    "image": { "type": "string" },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "guild_id", "user_id", "channel_id", "channel_name", "message_id", "message", "image", "timestamp"]
}
```
