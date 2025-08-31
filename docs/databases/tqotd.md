# tqotd

This document describes the structure of the `tqotd` collection used in TacoBot. Each document represents a Taco Question of the Day in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **timestamp**: *(number)*  
  The time the question was posted (epoch).
- **answered**: *(array of strings)*  
  List of user IDs who answered.
- **author**: *(string)*  
  The author of the question.
- **question**: *(string)*  
  The question text.

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "timestamp": 1693459200,
  "answered": ["987654321098765432"],
  "author": "TacoBot",
  "question": "What's your favorite taco?"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TQOTD",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "timestamp": { "type": "number" },
    "answered": { "type": "array", "items": { "type": "string" } },
    "author": { "type": "string" },
    "question": { "type": "string" }
  },
  "required": ["_id", "guild_id", "timestamp", "answered", "author", "question"]
}
```
