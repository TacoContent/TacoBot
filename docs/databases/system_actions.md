# system_actions

This document describes the structure of the `system_actions` collection used in TacoBot. Each document in this collection represents a system action event in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **action**: *(string)*  
  The action performed.
- **timestamp**: *(number)*  
  The time the action occurred (epoch).
- **data**: *(object)*  
  Additional data about the action, may include:
  - **user_id**: *(string)*
  - **reason**: *(string)*
  - **account_age**: *(number)*

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "action": "ban",
  "timestamp": 1693459200,
  "data": {
    "user_id": "987654321098765432",
    "reason": "Spam",
    "account_age": 365
  }
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SystemAction",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "action": { "type": "string", "description": "Action performed" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" },
    "data": {
      "type": "object",
      "properties": {
        "user_id": { "type": "string" },
        "reason": { "type": "string" },
        "account_age": { "type": "number" }
      }
    }
  },
  "required": ["_id", "guild_id", "action", "timestamp"]
}
```
