# minecraft_users

This document describes the structure of the `minecraft_users` collection used in TacoBot. Each document represents a Minecraft user associated with a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **user_id**: *(string)*  
  The Discord user ID.
- **uuid**: *(string)*  
  The Minecraft UUID.
- **username**: *(string)*  
  The Minecraft username.
- **whitelist**: *(boolean)*  
  Whether the user is whitelisted.
- **op**: *(object)*  
  Operator status, including:
  - **enabled**: *(boolean)*
  - **level**: *(number)*
  - **bypassesPlayerLimit**: *(boolean)*
- **guild_id**: *(string)*  
  The Discord guild (server) ID.

## Example

```json
{
  "_id": "ObjectId('...')",
  "user_id": "987654321098765432",
  "uuid": "minecraft-uuid",
  "username": "Steve",
  "whitelist": true,
  "op": { "enabled": true, "level": 4, "bypassesPlayerLimit": false },
  "guild_id": "123456789012345678"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MinecraftUser",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "user_id": { "type": "string" },
    "uuid": { "type": "string" },
    "username": { "type": "string" },
    "whitelist": { "type": "boolean" },
    "op": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean" },
        "level": { "type": "number" },
        "bypassesPlayerLimit": { "type": "boolean" }
      },
      "required": ["enabled", "level", "bypassesPlayerLimit"]
    },
    "guild_id": { "type": "string" }
  },
  "required": ["_id", "user_id", "uuid", "username", "whitelist", "op", "guild_id"]
}
```
