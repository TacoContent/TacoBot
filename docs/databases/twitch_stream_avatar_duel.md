# Collection: twitch_stream_avatar_duel

This collection stores records of avatar duels that occur during Twitch streams. Each document represents a duel event and its participants.

## Document Structure
- `_id`: ObjectId
- `guild_id`: String
- `challenger`: String
- `challenger_user_id`: String
- `channel`: String
- `channel_user_id`: String
- `count`: Number
- `opponent`: String
- `opponent_user_id`: String
- `timestamp`: Number
- `type`: String
- `winner`: String
- `winner_user_id`: String

## Example Document
```json
{
  "_id": "ObjectId(...)" ,
  "guild_id": "1234567890",
  "challenger": "userA",
  "challenger_user_id": "1111111111",
  "channel": "twitch_channel",
  "channel_user_id": "3333333333",
  "count": 1,
  "opponent": "userB",
  "opponent_user_id": "2222222222",
  "timestamp": 1693449600,
  "type": "duel",
  "winner": "userA",
  "winner_user_id": "1111111111"
}
```


## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TwitchStreamAvatarDuel",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId" },
    "guild_id": { "type": "string" },
    "challenger": { "type": "string" },
    "challenger_user_id": { "type": "string" },
    "channel": { "type": "string" },
    "channel_user_id": { "type": "string" },
    "count": { "type": "number" },
    "opponent": { "type": "string" },
    "opponent_user_id": { "type": "string" },
    "timestamp": { "type": "number" },
    "type": { "type": "string" },
    "winner": { "type": "string" },
    "winner_user_id": { "type": "string" }
  },
  "required": ["_id", "guild_id", "challenger", "challenger_user_id", "channel", "channel_user_id", "count", "opponent", "opponent_user_id", "timestamp", "type", "winner", "winner_user_id"]
}
```
