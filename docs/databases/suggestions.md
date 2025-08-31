# suggestions

This document describes the structure of the `suggestions` collection used in TacoBot. Each document represents a suggestion submitted by a user in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **id**: *(string)*  
  The suggestion ID.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **author_id**: *(string)*  
  The Discord user ID of the author.
- **message_id**: *(string)*  
  The Discord message ID.
- **actions**: *(array of objects)*  
  Actions taken on the suggestion, each with:
  - **state**: *(string)*
  - **user_id**: *(string)*
  - **reason**: *(string)*
  - **timestamp**: *(number)*
- **votes**: *(array of objects)*  
  Votes on the suggestion, each with:
  - **user_id**: *(string)*
  - **vote**: *(number)*
  - **timestamp**: *(number)*
- **suggestion**: *(object)*  
  The suggestion details:
  - **title**: *(string)*
  - **description**: *(string)*
- **state**: *(string)*  
  The current state of the suggestion.
- **timestamp**: *(number)*  
  The time the suggestion was submitted (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "id": "sug-001",
  "guild_id": "123456789012345678",
  "author_id": "987654321098765432",
  "message_id": "345678901234567890",
  "actions": [
    {"state": "approved", "user_id": "admin123", "reason": "Good idea", "timestamp": 1693459300}
  ],
  "votes": [
    {"user_id": "user456", "vote": 1, "timestamp": 1693459400}
  ],
  "suggestion": {"title": "Add new feature", "description": "Please add..."},
  "state": "pending",
  "timestamp": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Suggestion",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "id": { "type": "string", "description": "Suggestion ID" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "author_id": { "type": "string", "description": "Author user ID" },
    "message_id": { "type": "string", "description": "Discord message ID" },
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "state": { "type": "string" },
          "user_id": { "type": "string" },
          "reason": { "type": "string" },
          "timestamp": { "type": "number" }
        },
        "required": ["state", "user_id", "reason", "timestamp"]
      }
    },
    "votes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "user_id": { "type": "string" },
          "vote": { "type": "number" },
          "timestamp": { "type": "number" }
        },
        "required": ["user_id", "vote", "timestamp"]
      }
    },
    "suggestion": {
      "type": "object",
      "properties": {
        "title": { "type": "string" },
        "description": { "type": "string" }
      },
      "required": ["title", "description"]
    },
    "state": { "type": "string" },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "id", "guild_id", "author_id", "message_id", "actions", "votes", "suggestion", "state", "timestamp"]
}
```
