# users

This document describes the structure of the `users` collection used in TacoBot. Each document represents a user in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **user_id**: *(string)*  
  The Discord user ID.
- **avatar**: *(string)*  
  The user's avatar URL.
- **bot**: *(boolean)*  
  Whether the user is a bot.
- **created**: *(number)*  
  The time the user was created (epoch).
- **discriminator**: *(string)*  
  The user's discriminator (e.g., "1234").
- **displayname**: *(string)*  
  The user's display name.
- **system**: *(boolean)*  
  Whether the user is a system user.
- **timestamp**: *(number)*  
  The time the user was added to the database (epoch).
- **username**: *(string)*  
  The user's username.
- **status**: *(string)*  
  The user's status (e.g., "online").

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "user_id": "987654321098765432",
  "avatar": "https://...",
  "bot": false,
  "created": 1693459200,
  "discriminator": "1234",
  "displayname": "TacoUser",
  "system": false,
  "timestamp": 1693459300,
  "username": "TacoUser",
  "status": "online"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "User",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "user_id": { "type": "string", "description": "Discord user ID" },
    "avatar": { "type": "string", "description": "Avatar URL" },
    "bot": { "type": "boolean", "description": "Bot status" },
    "created": { "type": "number", "description": "User creation time" },
    "discriminator": { "type": "string", "description": "Discriminator" },
    "displayname": { "type": "string", "description": "Display name" },
    "system": { "type": "boolean", "description": "System user status" },
    "timestamp": { "type": "number", "description": "Database timestamp" },
    "username": { "type": "string", "description": "Username" },
    "status": { "type": "string", "description": "User status" }
  },
  "required": ["_id", "guild_id", "user_id", "avatar", "bot", "created", "discriminator", "displayname", "system", "timestamp", "username", "status"]
}
```
