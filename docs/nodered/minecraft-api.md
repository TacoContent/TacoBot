# Node-RED Flows: Minecraft API

This documentation describes the available HTTP endpoints and main flows defined in the `minecraft-api.json` Node-RED configuration.

## HTTP Endpoints

### GET `/tacobot/minecraft/whitelist.json`

- **Description:** Returns a list of whitelisted Minecraft users.
- **Response:**
  - JSON array of objects: `[ { "uuid": string, "name": string } ]`

### GET `/tacobot/minecraft/ops.json`

- **Description:** Returns a list of Minecraft server operators (OPs).
- **Response:**
  - JSON array of objects: `[ { "uuid": string, "name": string, "level": number, "bypassesPlayerLimit": boolean } ]`

### GET `/tacobot/minecraft/uuid/:username`

- **Description:** Looks up the UUID for a given Minecraft username using Mojang's API.
- **Response:**
  - `{ "name": string, "uuid": string }` or `{ "error": code }`

### GET `/tacobot/minecraft/status`

- **Description:** Returns the status of the Minecraft server (online/offline, player count, version, etc).
- **Response:**
  - JSON object: `{ success, host, title, status, online, players: { max, online }, version }`

## MQTT Integration

- Publishes Minecraft server status and availability to MQTT topics `minecraft/status` and `minecraft/availability`.

## Main Flows

- **Whitelist Query:**
  - Queries the `minecraft_users` MongoDB collection for users with `whitelist: true`.
- **OPs Query:**
  - Queries the `minecraft_users` collection for users with `whitelist: true` and `op.enabled: true`.
- **UUID Lookup:**
  - Uses Mojang's API to resolve a username to a UUID.
- **Status Check:**
  - Pings the Minecraft server and formats the response for HTTP and MQTT.

## Error Handling

- Catches and logs exceptions in the Minecraft ping/status flows.

---

For more details, see the Node-RED flow file: [`nodered/minecraft-api.json`](../../nodered/minecraft-api.json)
