# TacoBot API Endpoints

This document describes the HTTP API endpoints exposed by TacoBot under `/api/v1/` and related routes.

---

## Endpoints

### `/api/v1/swagger.yaml`

- **Method:** GET

- **Description:** Returns the OpenAPI/Swagger YAML file describing the API.

- **Input:** None

- **Output:** YAML (OpenAPI spec)

- **Status Codes:**
  - 200: Success

### `/api/v1/minecraft/whitelist.json`

- **Method:** GET

- **Description:** Returns the Minecraft whitelist as JSON.

- **Input:** None

- **Output:** Array of objects:
  - `uuid` (string)
  - `username` (string)

- **Status Codes:**
  - 200: Success

### `/api/v1/minecraft/ops.json`

- **Method:** GET

- **Description:** Returns the Minecraft ops list as JSON.

- **Input:** None

- **Output:** Array of objects:
  - `uuid` (string)
  - `username` (string)
  - `level` (integer)
  - `bypassPlayerLimit` (boolean)

- **Status Codes:**
  - 200: Success

### `/api/v1/minecraft/uuid/{username}`

- **Method:** GET

- **Description:** Get Minecraft user info by username.

- **Input:** Path parameter `username` (string)

- **Output:**
  - 200: `{ uuid: string, name: string }`
  - 500: `{ error: integer }`

### `/api/v1/minecraft/status`

- **Method:** GET

- **Description:** Get Minecraft server status.

- **Input:** None

- **Output:**
  - `success` (boolean)
  - `host` (string)
  - `status` ("online"|"offline")
  - `description` (string)
  - `motd` (object)
  - `online` (boolean)
  - `latency` (number)
  - `enforces_secure_chat` (boolean)
  - `icon` (string)
  - `players` (object)
  - `version` (object)

- **Status Codes:**
  - 200: Success

### `/api/v1/minecraft/version`

- **Method:** GET, POST

- **Description:** Get or set Minecraft server version info.

- **Input:**
  - GET: None
  - POST: JSON body (see `TacoMinecraftServerSettings` schema)

- **Output:** JSON (see `TacoMinecraftServerSettings` schema)

- **Status Codes:**
  - 200: Success

### `/api/v1/minecraft/player/{user}/stats`

- **Method:** GET, POST

- **Description:** Get or set player stats.

- **Input:**
  - Path parameter `user` (string)
  - POST: JSON body (see `MinecraftUserStatsPayload` schema)

- **Output:**
  - GET: `MinecraftDiscordUserStatsInfo` object
  - POST: 200 OK

### `/api/v1/minecraft/player/{username}/stats/{world}`

- **Method:** GET

- **Description:** Get player stats for a specific world.

- **Input:** Path parameters `username` (string), `world` (string)

- **Output:** `MinecraftDiscordUserStatsInfo` object

- **Status Codes:**
  - 200: Success

### `/api/v1/minecraft/world`

- **Method:** GET, POST

- **Description:** Get or set the active Minecraft world.

- **Input:**
  - GET: None
  - POST: JSON body `{ guild_id: string, world: string }`

- **Output:** `TacoMinecraftWorldInfo` object

- **Status Codes:**
  - 200: Success

### `/api/v1/minecraft/worlds`

- **Method:** GET

- **Description:** Get all Minecraft worlds info.

- **Input:** None

- **Output:** Array of `TacoMinecraftWorldInfo` objects

- **Status Codes:**
  - 200: Success

### `/api/v1/minecraft/player/events`

- **Method:** GET

- **Description:** Get all Minecraft player events.

- **Input:** None

- **Output:** Array of `MinecraftPlayerEvent` objects

- **Status Codes:**
  - 200: Success

### `/api/v1/minecraft/player/event/{event}`

- **Method:** GET

- **Description:** Get a specific Minecraft player event.

- **Input:** Path parameter `event` (string)

- **Output:** `MinecraftPlayerEventPayload` object

- **Status Codes:**
  - 200: Success


### `/api/v1/permissions/{guildId}/{userId}`

- **Method:** GET
- **Description:** Get all permissions for a user in a guild.
- **Input:**
  - Path parameters:
    - `guildId` (string): Discord Guild ID
    - `userId` (string): Discord User ID
- **Output:**
  - 200: Array of permission strings

### `/api/v1/permissions/{guildId}/{userId}/{permission}`

- **Method:** POST
- **Description:** Add a permission to a user in a guild.
- **Input:**
  - Path parameters:
    - `guildId` (string): Discord Guild ID
    - `userId` (string): Discord User ID
    - `permission` (string): Permission name
- **Output:**
  - 200: OK

- **Method:** PUT
- **Description:** Add (or update) a permission for a user in a guild.
- **Input:**
  - Path parameters:
    - `guildId` (string): Discord Guild ID
    - `userId` (string): Discord User ID
    - `permission` (string): Permission name
- **Output:**
  - 200: OK

- **Method:** DELETE
- **Description:** Remove a permission from a user in a guild.
- **Input:**
  - Path parameters:
    - `guildId` (string): Discord Guild ID
    - `userId` (string): Discord User ID
    - `permission` (string): Permission name
- **Output:**
  - 200: OK

---

See the OpenAPI spec for full schema details.
