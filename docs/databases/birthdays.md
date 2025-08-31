# Birthdays

This document describes the structure of the `birthdays` collection used in TacoBot. Each document in this collection represents a user's birthday within a specific Discord guild (server).

## Document Structure

- **_id**: *(string)*  
  The unique identifier for the birthday record, represented as a MongoDB ObjectId string.

- **guild_id**: *(string)*  
  The Discord guild (server) ID where the birthday is registered.

- **user_id**: *(string)*  
  The Discord user ID whose birthday is being tracked.

- **day**: *(integer)*  
  The day of the user's birthday (1-31).

- **month**: *(integer)*  
  The month of the user's birthday (1-12).

- **timestamp**: *(number)*  
  The timestamp (as a float) when the birthday was recorded.

All fields are required.

## Example

```json
{
  "_id": "623276dd40e9bfc3478a793a",
  "guild_id": "935294040386183228",
  "user_id": "270071773297508353",
  "day": 20,
  "month": 3,
  "timestamp": 1647474397.57997
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Birthday",
  "type": "object",
  "properties": {
    "_id": {
      "description": "MongoDB ObjectId as a string",
      "type": "string"
    },
    "guild_id": {
      "description": "Discord guild/server ID",
      "type": "string"
    },
    "user_id": {
      "description": "Discord user ID",
      "type": "string"
    },
    "day": {
      "description": "Day of the birthday (1-31)",
      "type": "integer",
      "minimum": 1,
      "maximum": 31
    },
    "month": {
      "description": "Month of the birthday (1-12)",
      "type": "integer",
      "minimum": 1,
      "maximum": 12
    },
    "timestamp": {
      "description": "Timestamp when the birthday was recorded (float)",
      "type": "number"
    }
  },
  "required": ["_id", "guild_id", "user_id", "day", "month", "timestamp"]
}
```