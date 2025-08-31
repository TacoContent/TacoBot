# twitch_tacos_gifts

This document describes the structure of the `twitch_tacos_gifts` collection used in TacoBot. Each document represents a record of tacos gifted via Twitch in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **channel**: *(string)*  
  The Twitch channel name or ID.
- **from_user_id**: *(string)*  
  The Discord user ID of the sender.
- **twitch_name**: *(string)*  
  The Twitch username of the sender.
- **to_user_id**: *(string)*  
  The Discord user ID of the recipient.
- **count**: *(number)*  
  The number of tacos gifted.
- **timestamp**: *(number)*  
  The time the gift was made (epoch).
- **reason**: *(string)*  
  The reason for the gift.

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "channel": "twitch_channel",
  "from_user_id": "111111111111111111",
  "twitch_name": "Streamer123",
  "to_user_id": "222222222222222222",
  "count": 5,
  "timestamp": 1693459200,
  "reason": "Great stream!"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TwitchTacosGift",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "channel": { "type": "string", "description": "Twitch channel name or ID" },
    "from_user_id": { "type": "string", "description": "Sender Discord user ID" },
    "twitch_name": { "type": "string", "description": "Sender Twitch username" },
    "to_user_id": { "type": "string", "description": "Recipient Discord user ID" },
    "count": { "type": "number", "description": "Number of tacos gifted" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" },
    "reason": { "type": "string", "description": "Reason for gift" }
  },
  "required": ["_id", "guild_id", "channel", "from_user_id", "twitch_name", "to_user_id", "count", "timestamp", "reason"]
}
```
