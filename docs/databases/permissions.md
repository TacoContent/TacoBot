# Permissions

This document describes the structure of the `permissions` collection used in TacoBot. Each document in this collection represents the permissions assigned to a specific user within a Discord guild (server).

These can be permissions to grant a specific action, or deny a specific action.

## Document Structure

- **_id**: *(string)*  
  The unique identifier for the permission document, represented as a MongoDB ObjectId string.

- **guild_id**: *(string)*  
  The Discord guild (server) ID to which these permissions apply.

- **user_id**: *(string)*  
  The Discord user ID for whom the permissions are set.

- **permissions**: *(array of strings)*  
  A list of permission flags assigned to the user in the specified guild. Each flag is a string representing a specific permission (e.g., `"claim_game_disabled"`, `"taco_receive_disabled"`).

All fields are required.

## Example

```json
{
  "_id": "60f7c2b8e1d2f8a1b4c8e9f1",
  "guild_id": "123456789012345678",
  "user_id": "987654321098765432",
  "permissions": ["claim_game_disabled"]
}
```

## Schema

``` json
  {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Permission",
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
      "permissions": {
        "description": "List of permission flags",
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "required": ["_id", "guild_id", "user_id", "permissions"]
  }
```
