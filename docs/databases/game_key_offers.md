# game_key_offers

This document describes the structure of the `game_key_offers` collection used in TacoBot. Each document represents an offer for a game key in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **game_key_id**: *(string)*  
  The ID of the game key being offered.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **channel_id**: *(string)*  
  The Discord channel ID.
- **expires**: *(number)*  
  When the offer expires (epoch).
- **message_id**: *(string)*  
  The Discord message ID.
- **timestamp**: *(number)*  
  The time the offer was made (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "game_key_id": "key-001",
  "guild_id": "123456789012345678",
  "channel_id": "234567890123456789",
  "expires": 1693462800,
  "message_id": "345678901234567890",
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GameKeyOffer",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "game_key_id": { "type": "string" },
    "guild_id": { "type": "string" },
    "channel_id": { "type": "string" },
    "expires": { "type": "number" },
    "message_id": { "type": "string" },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "game_key_id", "guild_id", "channel_id", "expires", "message_id", "timestamp"]
}
```
