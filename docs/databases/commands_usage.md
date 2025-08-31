# commands_usage

This document describes the structure of the `commands_usage` collection used in TacoBot. Each document represents a command usage event in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **channel_id**: *(string)*  
  The Discord channel ID.
- **user_id**: *(string)*  
  The Discord user ID.
- **command**: *(string)*  
  The command used.
- **subcommand**: *(string)*  
  The subcommand used.
- **arguments**: *(array of objects)*  
  Arguments for the command, each with:
  - **type**: *(string)*
  - **payload**: *(object)* (may include message_id, channel_id, guild_id, user_id, emoji, event_type)
- **timestamp**: *(number)*  
  The time the command was used (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "channel_id": "234567890123456789",
  "user_id": "987654321098765432",
  "command": "taco",
  "subcommand": "give",
  "arguments": [
    {"type": "user", "payload": {"user_id": "123456789012345678"}}
  ],
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CommandUsage",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "channel_id": { "type": "string" },
    "user_id": { "type": "string" },
    "command": { "type": "string" },
    "subcommand": { "type": "string" },
    "arguments": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": { "type": "string" },
          "payload": { "type": "object" }
        },
        "required": ["type", "payload"]
      }
    },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "guild_id", "channel_id", "user_id", "command", "subcommand", "arguments", "timestamp"]
}
```
