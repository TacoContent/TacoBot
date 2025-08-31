# Collection: tacos_log

This collection logs all taco transactions between users in a guild. Each document records a transfer of tacos, including sender, recipient, count, type, and reason.

## Document Structure
- `_id`: ObjectId
- `guild_id`: String (Discord server ID)
- `from_user_id`: String (sender)
- `to_user_id`: String (recipient)
- `count`: Number (number of tacos transferred)
- `type`: String (transaction type)
- `reason`: String (reason for transfer)
- `timestamp`: Number (when the transaction occurred)

## Example Document
```json
{
  "_id": "ObjectId(...)" ,
  "guild_id": "1234567890",
  "from_user_id": "1111111111",
  "to_user_id": "2222222222",
  "count": 3,
  "type": "gift",
  "reason": "helpful answer",
  "timestamp": 1693449600
}
```


## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TacosLog",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId" },
    "guild_id": { "type": "string" },
    "from_user_id": { "type": "string" },
    "to_user_id": { "type": "string" },
    "count": { "type": "number" },
    "type": { "type": "string" },
    "reason": { "type": "string" },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "guild_id", "from_user_id", "to_user_id", "count", "type", "reason", "timestamp"]
}
```
