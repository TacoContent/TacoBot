# minecraft_ping

This document describes the structure of the `minecraft_ping` collection used in TacoBot. Each document represents a Minecraft server ping result in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **players**: *(object)*  
  Player stats, including:
  - **max**: *(number)*
  - **online**: *(number)*
- **up**: *(number)*  
  Server up status (1 for up, 0 for down).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "players": { "max": 20, "online": 5 },
  "up": 1
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MinecraftPing",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "players": {
      "type": "object",
      "properties": {
        "max": { "type": "number" },
        "online": { "type": "number" }
      },
      "required": ["max", "online"]
    },
    "up": { "type": "number" }
  },
  "required": ["_id", "guild_id", "players", "up"]
}
```
