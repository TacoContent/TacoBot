# Collection: settings

This collection stores configuration and settings for each guild (server) in TacoBot. Each document represents a set of settings for a guild, including limits, channel IDs, command prefixes, and other bot configuration options.

## Document Structure
- `_id`: ObjectId
- `guild_id`: String (Discord server ID)
- `name`: String (settings name)
- `settings`: Document (various configuration fields, see schema)
- `timestamp`: Number (last updated)

## Example Document
```json
{
  "_id": "ObjectId(...)" ,
  "guild_id": "1234567890",
  "name": "default",
  "settings": {
    "taco_log_channel_id": "9876543210",
    "reaction_emoji": ":taco:",
    "reaction_emojis": [":taco:", ":burrito:"],
    "max_gift_tacos": 5,
    "max_gift_taco_timespan": 3600,
    "api_max_give_per_user_per_timespan": 10,
    "api_max_give_per_user": 20,
    "api_max_give_total_per_timespan": 100,
    "api_max_give_timespan": 86400,
    "reaction_count": 0,
    "join_count": 0,
    "boost_count": 0,
    "reaction_reward_count": 0,
    "suggest_count": 0,
    "invite_count": 0,
    "reply_count": 0,
    "tqotd_count": 0,
    "birthday_count": 0,
    "twitch_count": 0,
    "stream_count": 0,
    "mentalmondays_count": 0,
    "wdyctw_count": 0,
    "tech_thursday_count": 0,
    "taco_tuesday_count": 0,
    "first_message_count": 0,
    "event_create_count": 0,
    "event_join_count": 0,
    "event_leave_count": 0,
    "event_cancel_count": 0,
    "twitch_bot_invite_count": 0,
    "twitch_raid_count": 0,
    "twitch_sub_count": 0,
    "twitch_bits_count": 0,
    "twitch_first_message_count": 0,
    "twitch_promote_count": 0,
    "twitch_follow_count": 0,
    "follow_channel_count": 0,
    "create_voice_channel_count": 0,
    "post_introduction_count": 0,
    "approve_introduction_count": 0,
    "suggestion_channel_ids": ["123", "456"],
    "cb_prefix": "!",
    "allowed_commands": "all",
    "channels": [],
    "command_prefixes": ["!", "/"],
    "presence": "online"
  },
  "timestamp": 1693449600
}
```


## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Settings",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId" },
    "guild_id": { "type": "string" },
    "name": { "type": "string" },
    "settings": { "type": "object" },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "guild_id", "name", "settings", "timestamp"]
}
```
