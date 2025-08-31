# game_keys

This document describes the structure of the `game_keys` collection used in TacoBot. Each document represents a game key available or redeemed in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **title**: *(string)*  
  The title of the game.
- **key**: *(string)*  
  The game key string.
- **type**: *(string)*  
  The type of key.
- **help_link**: *(null)*  
  Help link (if any).
- **download_link**: *(null)*  
  Download link (if any).
- **info_link**: *(string)*  
  Info link for the game.
- **user_owner**: *(string)*  
  The Discord user ID of the key owner.
- **redeemed_by**: *(string|null)*  
  The Discord user ID who redeemed the key (if any).
- **redeemed_timestamp**: *(number|null)*  
  When the key was redeemed (epoch or null).
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **cost**: *(number)*  
  The cost of the key (if any).

## Example

```json
{
  "_id": "ObjectId('...')",
  "title": "Cool Game",
  "key": "XXXX-YYYY-ZZZZ",
  "type": "steam",
  "help_link": null,
  "download_link": null,
  "info_link": "https://...",
  "user_owner": "987654321098765432",
  "redeemed_by": null,
  "redeemed_timestamp": null,
  "guild_id": "123456789012345678",
  "cost": 0
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GameKey",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "title": { "type": "string" },
    "key": { "type": "string" },
    "type": { "type": "string" },
    "help_link": { "type": ["null"] },
    "download_link": { "type": ["null"] },
    "info_link": { "type": "string" },
    "user_owner": { "type": "string" },
    "redeemed_by": { "type": ["string", "null"] },
    "redeemed_timestamp": { "type": ["number", "null"] },
    "guild_id": { "type": "string" },
    "cost": { "type": "number" }
  },
  "required": ["_id", "title", "key", "type", "help_link", "download_link", "info_link", "user_owner", "redeemed_by", "redeemed_timestamp", "guild_id", "cost"]
}
```
