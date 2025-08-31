# Free Game Keys

This document describes the structure of the `free_game_keys` collection used in TacoBot. Each document in this collection represents a free game key or giveaway offer, including all relevant details for display and redemption.

## Document Structure

- **_id**: *(string)*  
  The unique identifier for the giveaway, represented as a MongoDB ObjectId string.

- **title**: *(string)*  
  The title of the game or giveaway.

- **worth**: *(string)*  
  The estimated value or worth of the key (e.g., "N/A" if not specified).

- **thumbnail**: *(string, uri)*  
  URL to a thumbnail image representing the giveaway.

- **image**: *(string, uri)*  
  URL to a main image for the giveaway.

- **description**: *(string)*  
  A description of the giveaway, including any relevant details about the game or event.

- **instructions**: *(string)*  
  Step-by-step instructions for redeeming the key.

- **open_giveaway_url**: *(string, uri)*  
  Direct URL to the giveaway page.

- **published_date**: *(integer)*  
  The published date of the giveaway as a Unix timestamp (seconds).

- **type**: *(string)*  
  The type of giveaway (e.g., "Early Access").

- **platforms**: *(array of strings)*  
  List of supported platforms for the key (e.g., `["PC"]`).

- **end_date**: *(integer)*  
  The end date of the giveaway as a Unix timestamp (seconds).

- **game_id**: *(integer)*  
  The identifier for the game.

- **formatted_published_date**: *(string)*  
  The published date in a human-readable format.

- **formatted_end_date**: *(string)*  
  The end date in a human-readable format.

All fields are required.

## Example

```json
{
  "_id": "66955aeb0fd27600075a2177",
  "title": "Pantheon: Rise of the Fallen Playtest Code",
  "worth": "N/A",
  "thumbnail": "https://www.gamerpower.com/offers/1/669158f65dfae.jpg",
  "image": "https://www.gamerpower.com/offers/1b/669158f65dfae.jpg",
  "description": "If you're an MMO fan, don't miss this giveaway! Grab your free Pantheon: Rise of the Fallen playtest code and be among the first to experience this game. Please note this playtest access will run between July 27 - August 3.",
  "instructions": "1. Click the \"Get Offer\" button to visit the giveaway page.\r\n2. Login into your free MMOBomb account and click the button to unlock your key.\r\n3. Follow the giveaway instructions to redeem your key.",
  "open_giveaway_url": "https://www.gamerpower.com/open/pantheon-rise-of-the-fallen-beta-code-giveaway",
  "published_date": 1720805126,
  "type": "Early Access",
  "platforms": [
    "PC"
  ],
  "end_date": 1722056399,
  "game_id": 2889,
  "formatted_published_date": "2024-07-12 12:25:26",
  "formatted_end_date": "2024-07-26 23:59:59"
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FreeGameKey",
  "type": "object",
  "properties": {
    "_id": {
      "description": "MongoDB ObjectId as a string",
      "type": "string"
    },
    "title": {
      "description": "Title of the game or giveaway",
      "type": "string"
    },
    "worth": {
      "description": "Estimated worth or value of the key",
      "type": "string"
    },
    "thumbnail": {
      "description": "Thumbnail image URL",
      "type": "string",
      "format": "uri"
    },
    "image": {
      "description": "Main image URL",
      "type": "string",
      "format": "uri"
    },
    "description": {
      "description": "Description of the giveaway",
      "type": "string"
    },
    "instructions": {
      "description": "Instructions to redeem the key",
      "type": "string"
    },
    "open_giveaway_url": {
      "description": "URL to open the giveaway",
      "type": "string",
      "format": "uri"
    },
    "published_date": {
      "description": "Published date as a Unix timestamp (seconds)",
      "type": "integer"
    },
    "type": {
      "description": "Type of giveaway (e.g., Early Access)",
      "type": "string"
    },
    "platforms": {
      "description": "List of supported platforms",
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "end_date": {
      "description": "End date as a Unix timestamp (seconds)",
      "type": "integer"
    },
    "game_id": {
      "description": "Game identifier",
      "type": "integer"
    },
    "formatted_published_date": {
      "description": "Published date in formatted string",
      "type": "string"
    },
    "formatted_end_date": {
      "description": "End date in formatted string",
      "type": "string"
    }
  },
  "required": [
    "_id",
    "title",
    "worth",
    "thumbnail",
    "image",
    "description",
    "instructions",
    "open_giveaway_url",
    "published_date",
    "type",
    "platforms",
    "end_date",
    "game_id",
    "formatted_published_date",
    "formatted_end_date"
  ]
}
```
