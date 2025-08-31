# invite_codes

This document describes the structure of the `invite_codes` collection used in TacoBot. Each document represents an invite code and its usage in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **code**: *(string)*  
  The invite code string.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **info**: *(object)*  
  Information about the invite, including:
  - **id**: *(string)*
  - **code**: *(string)*
  - **inviter_id**: *(string)*
  - **uses**: *(number)*
  - **max_uses**: *(number)*
  - **max_age**: *(number)*
  - **temporary**: *(boolean)*
  - **created_at**: *(date)*
  - **revoked**: *(null)*
  - **channel_id**: *(string)*
  - **url**: *(string)*
- **timestamp**: *(number)*  
  The time the invite was created (epoch).
- **invites**: *(array of objects)*  
  List of invite uses, each with:
  - **user_id**: *(string)*
  - **timestamp**: *(number)*

## Example

```json
{
  "_id": "ObjectId('...')",
  "code": "abc123",
  "guild_id": "123456789012345678",
  "info": {
    "id": "inviteid",
    "code": "abc123",
    "inviter_id": "987654321098765432",
    "uses": 5,
    "max_uses": 10,
    "max_age": 86400,
    "temporary": false,
    "created_at": "2023-01-01T00:00:00Z",
    "revoked": null,
    "channel_id": "234567890123456789",
    "url": "https://discord.gg/abc123"
  },
  "timestamp": 1693459200,
  "invites": [
    {"user_id": "user1", "timestamp": 1693459300}
  ]
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "InviteCode",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "code": { "type": "string", "description": "Invite code" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "info": {
      "type": "object",
      "properties": {
        "id": { "type": "string" },
        "code": { "type": "string" },
        "inviter_id": { "type": "string" },
        "uses": { "type": "number" },
        "max_uses": { "type": "number" },
        "max_age": { "type": "number" },
        "temporary": { "type": "boolean" },
        "created_at": { "type": "string", "format": "date-time" },
        "revoked": { "type": ["null"] },
        "channel_id": { "type": "string" },
        "url": { "type": "string" }
      }
    },
    "timestamp": { "type": "number", "description": "Epoch timestamp" },
    "invites": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "user_id": { "type": "string" },
          "timestamp": { "type": "number" }
        },
        "required": ["user_id", "timestamp"]
      }
    }
  },
  "required": ["_id", "code", "guild_id", "info", "timestamp", "invites"]
}
```
