# Collection: twitch_first_message

This collection stores the first message sent by a Twitch user in a channel, for tracking and engagement purposes.

## Document Structure
- `_id`: ObjectId
- `guild_id`: String (Discord server ID)
- `channel`: String (Twitch channel name)
- `twitch_name`: String (Twitch username)
- `message`: String (first message content)
- `timestamp`: Number (when the message was sent)

## Example Document
```json
{
  "_id": "ObjectId(...)" ,
  "guild_id": "1234567890",
  "channel": "twitch_channel",
  "twitch_name": "user123",
  "message": "Hello, world!",
  "timestamp": 1693449600
}
```


## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TwitchFirstMessage",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId" },
    "guild_id": { "type": "string" },
    "channel": { "type": "string" },
    "twitch_name": { "type": "string" },
    "message": { "type": "string" },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "guild_id", "channel", "twitch_name", "message", "timestamp"]
}
```
