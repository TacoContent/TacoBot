# twitch_user

This document describes the structure of the `twitch_user` collection used in TacoBot. Each document represents a Twitch user associated with a Discord user.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **user_id**: *(string)*  
  The Discord user ID.
- **twitch_id**: *(null)*  
  The Twitch user ID (if any).
- **twitch_name**: *(string)*  
  The Twitch username.

## Example

```json
{
  "_id": "ObjectId('...')",
  "user_id": "987654321098765432",
  "twitch_id": null,
  "twitch_name": "Streamer123"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TwitchUser",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "user_id": { "type": "string" },
    "twitch_id": { "type": ["null"] },
    "twitch_name": { "type": "string" }
  },
  "required": ["_id", "user_id", "twitch_id", "twitch_name"]
}
```
