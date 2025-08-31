# minecraft_worlds

This document describes the structure of the `minecraft_worlds` collection used in TacoBot. Each document represents a Minecraft world associated with a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **name**: *(string)*  
  The name of the Minecraft world.
- **world**: *(string)*  
  The world data or identifier.
- **active**: *(boolean)*  
  Whether the world is currently active.

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "name": "SurvivalWorld",
  "world": "world_1",
  "active": true
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MinecraftWorld",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "name": { "type": "string", "description": "World name" },
    "world": { "type": "string", "description": "World data or identifier" },
    "active": { "type": "boolean", "description": "Active status" }
  },
  "required": ["_id", "guild_id", "name", "world", "active"]
}
```
