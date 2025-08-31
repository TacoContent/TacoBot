# Collection: minecraft_stats

This collection stores Minecraft statistics for users, including crafted items, broken tools, picked up items, and more. Each document represents a user's stats in a Minecraft world.

## Document Structure
- `_id`: ObjectId
- `uuid`: String (Minecraft user UUID)
- `modified`: Number (last modified timestamp)
- `world`: String (world name)
- `stats`: Document (various Minecraft stats, see schema)
- `user_id`: String (optional, Discord user ID)
- `username`: String (optional, Minecraft username)

## Example Document
```json
{
  "_id": "ObjectId(...)" ,
  "uuid": "minecraft-uuid-1234",
  "modified": 1693449600,
  "world": "world",
  "stats": {
    "minecraft:crafted": { "minecraft:diamond_sword": 1 },
    "minecraft:broken": { "minecraft:iron_pickaxe": 2 },
    "minecraft:picked_up": { "minecraft:diamond": 5 },
    "minecraft:killed_by": { "minecraft:zombie": 3 },
    "minecraft:used": { "minecraft:torch": 10 },
    "minecraft:custom": { "minecraft:jump": 100 },
    "minecraft:mined": { "minecraft:stone": 200 }
  },
  "user_id": "1111111111",
  "username": "Steve"
}
```


## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MinecraftStats",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId" },
    "uuid": { "type": "string" },
    "modified": { "type": "number" },
    "world": { "type": "string" },
    "stats": { "type": "object" },
    "user_id": { "type": "string" },
    "username": { "type": "string" }
  },
  "required": ["_id", "uuid", "modified", "world", "stats"]
}
```
