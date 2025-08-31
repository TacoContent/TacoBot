# taco_gifts

This document describes the structure of the `taco_gifts` collection used in TacoBot. Each document in this collection represents a record of tacos gifted by a user in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **user_id**: *(string)*  
  The Discord user ID who gifted tacos.
- **count**: *(number)*  
  The number of tacos gifted.
- **timestamp**: *(number)*  
  The time the gift was made (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "user_id": "987654321098765432",
  "count": 5,
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TacoGift",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "user_id": { "type": "string", "description": "Discord user ID" },
    "count": { "type": "number", "description": "Number of tacos gifted" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" }
  },
  "required": ["_id", "guild_id", "user_id", "count", "timestamp"]
}
```
