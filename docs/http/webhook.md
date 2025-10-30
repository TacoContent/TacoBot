# TacoBot Webhook Endpoints

This document describes the HTTP Webhook endpoints exposed by TacoBot under `/webhook/` and related routes.

---

## Endpoints

### `/webhook/minecraft/tacos/{action}`

- **Method:** POST, DELETE
- **Description:** Minecraft Webhook to give or remove tacos to/from a user.
- **Input:**
  - Path parameter `action` (string, enum: `login`, `custom`)
  - JSON body (see `TacoWebhookMinecraftTacosPayload` schema):
    - `guild_id` (string)
    - `from_user` (string)
    - `to_user_id` (string)
    - `amount` (integer)
    - `reason` (string)
    - `type` (string, enum: `login`, `custom`)
- **Output:**
  - 200: `TacoWebhookMinecraftTacosResponsePayload` object:
    - `success` (boolean)
    - `payload` (TacoWebhookMinecraftTacosPayload)
    - `total_tacos` (integer)
- **Status Codes:**
  - 200: Success

### `/webhook/minecraft/player/event`

- **Method:** POST
- **Description:** Minecraft Webhook to send player events.
- **Input:**
  - JSON body (see `MinecraftPlayerEventPayload` schema):
    - `event` (string)
    - `guild_id` (string)
    - `payload` (object, varies by event)
- **Output:**
  - 200: `MinecraftPlayerEventPayload` object
- **Status Codes:**
  - 200: Success

### `/webhook/game`

- **Method:** POST
- **Description:** Submit Free Game Webhook.
- **Input:**
  - JSON body (see `TacoWebhookGamePayload` schema):
    - `game_id` (integer)
    - `end_date` (number)
    - `worth` (string)
    - `open_giveaway_url` (string)
    - `title` (string)
    - `thumbnail` (string)
    - `image` (string)
    - `description` (string)
    - `instructions` (string)
    - `published_date` (number)
    - `type` (string)
    - `platforms` (array of string)
    - `formatted_published_date` (string)
    - `formatted_end_date` (string)
- **Output:**
  - 200: `TacoWebhookGamePayload` object
- **Status Codes:**
  - 200: Success

---

See the OpenAPI spec for full schema details.
