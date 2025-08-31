# Collection: messages

This collection stores message history for users in a guild. Each document contains a user's messages, grouped by guild.

## Document Structure
- `_id`: ObjectId
- `guild_id`: String (Discord server ID)
- `user_id`: String (user ID)
- `messages`: Array of documents (each with `channel_id`, `message_id`, `timestamp`)

## Example Document
```json
{
  "_id": "ObjectId(...)" ,
  "guild_id": "1234567890",
  "user_id": "1111111111",
  "messages": [
    { "channel_id": "9876543210", "message_id": "5555555555", "timestamp": 1693449600 }
  ]
}
```


## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Messages",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId" },
    "guild_id": { "type": "string" },
    "user_id": { "type": "string" },
    "messages": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "channel_id": { "type": "string" },
          "message_id": { "type": "string" },
          "timestamp": { "type": "number" }
        },
        "required": ["channel_id", "message_id", "timestamp"]
      }
    }
  },
  "required": ["_id", "guild_id", "user_id", "messages"]
}
```
