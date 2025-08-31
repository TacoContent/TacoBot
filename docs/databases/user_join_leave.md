# user_join_leave

This document describes the structure of the `user_join_leave` collection used in TacoBot. Each document in this collection represents a user join or leave event in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **user_id**: *(string)*  
  The Discord user ID.
- **action**: *(string)*  
  The action taken (e.g., "join", "leave").
- **timestamp**: *(number)*  
  The time the event occurred (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "user_id": "987654321098765432",
  "action": "join",
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "UserJoinLeave",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "user_id": { "type": "string", "description": "Discord user ID" },
    "action": { "type": "string", "description": "Action taken (join/leave)" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" }
  },
  "required": ["_id", "guild_id", "user_id", "action", "timestamp"]
}
```
