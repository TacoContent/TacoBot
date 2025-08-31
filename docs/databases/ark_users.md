# ark_users

This document describes the structure of the `ark_users` collection used in TacoBot. Each document in this collection represents a user's ARK game accounts and permissions in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **user_id**: *(string)*  
  The Discord user ID.
- **platforms**: *(object)*  
  Platform accounts, e.g.:
  - **steam**: *(object)* { **id**: *(string)* }
  - **eos**: *(object)* { **id**: *(string)* }
- **games**: *(object)*  
  Game-specific permissions, e.g.:
  - **ark-sa**: *(object)* { **admin**: *(boolean)*, **whitelist**: *(boolean)*, **bypass**: *(boolean)* }

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "user_id": "987654321098765432",
  "platforms": {
    "steam": { "id": "steamid123" },
    "eos": { "id": "eosid456" }
  },
  "games": {
    "ark-sa": { "admin": true, "whitelist": false, "bypass": false }
  }
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ArkUser",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "user_id": { "type": "string", "description": "Discord user ID" },
    "platforms": {
      "type": "object",
      "properties": {
        "steam": { "type": "object", "properties": { "id": { "type": "string" } }, "required": ["id"] },
        "eos": { "type": "object", "properties": { "id": { "type": "string" } }, "required": ["id"] }
      }
    },
    "games": {
      "type": "object",
      "properties": {
        "ark-sa": {
          "type": "object",
          "properties": {
            "admin": { "type": "boolean" },
            "whitelist": { "type": "boolean" },
            "bypass": { "type": "boolean" }
          },
          "required": ["admin", "whitelist", "bypass"]
        }
      }
    }
  },
  "required": ["_id", "guild_id", "user_id", "platforms", "games"]
}
```
