# guilds

This document describes the structure of the `guilds` collection used in TacoBot. Each document represents a Discord guild (server).

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **created_at**: *(number)*  
  When the guild was created (epoch).
- **icon**: *(string)*  
  The guild's icon URL.
- **name**: *(string)*  
  The guild's name.
- **owner_id**: *(string)*  
  The Discord user ID of the guild owner.
- **timestamp**: *(number)*  
  The time the guild was added to the database (epoch).
- **vanity_url**: *(null)*  
  The guild's vanity URL (if any).
- **vanity_url_code**: *(null)*  
  The vanity URL code (if any).

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "created_at": 1693459200,
  "icon": "https://...",
  "name": "TacoGuild",
  "owner_id": "987654321098765432",
  "timestamp": 1693459300,
  "vanity_url": null,
  "vanity_url_code": null
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Guild",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "created_at": { "type": "number" },
    "icon": { "type": "string" },
    "name": { "type": "string" },
    "owner_id": { "type": "string" },
    "timestamp": { "type": "number" },
    "vanity_url": { "type": ["null"] },
    "vanity_url_code": { "type": ["null"] }
  },
  "required": ["_id", "guild_id", "created_at", "icon", "name", "owner_id", "timestamp", "vanity_url", "vanity_url_code"]
}
```
