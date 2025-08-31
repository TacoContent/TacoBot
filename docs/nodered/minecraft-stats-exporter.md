# Node-RED Flows: Minecraft Stats Exporter

This documentation describes the available HTTP endpoints and main flows defined in the `minecraft-stats-exporter.json` Node-RED configuration.

## HTTP Endpoints

### GET `/taco/minecraft/stats/metrics` and `/tacobot/minecraft/stats/metrics`

- **Description:**
  - Returns Minecraft player and server metrics in Prometheus text format.
  - Aggregates data from the `minecraft_stats`, `minecraft_worlds`, and `minecraft_ping` MongoDB collections, as well as mod settings.
- **Response:**
  - `text/plain` Prometheus metrics (e.g., `mcstats_players_online`, `mcstats_mod`, etc.)

### POST `/taco/minecraft/server/start` and `/tacobot/minecraft/server/start`

- **Description:** Starts the Minecraft server via Docker.
- **Response:** `{ success: true, status: "success" }` on success.

### POST `/taco/minecraft/server/stop` and `/tacobot/minecraft/server/stop`

- **Description:** Stops the Minecraft server via Docker.
- **Response:** `{ success: true, status: "success" }` on success.

### POST `/taco/minecraft/server/restart` and `/tacobot/minecraft/server/restart`

- **Description:** Restarts the Minecraft server via Docker.
- **Response:** `{ success: true, status: "success" }` on success.

## Main Flows

- **Metrics Aggregation:**
  - Collects player stats, mod info, world info, and server status from MongoDB.
  - Formats and exposes metrics for Prometheus scraping.
- **Server Control:**
  - Provides HTTP endpoints to start, stop, and restart the Minecraft server using Docker actions.
- **Ping/Status Update:**
  - Periodically pings the Minecraft server and updates the `minecraft_ping` collection with player counts and status.

## Error Handling

- Catches and formats errors for metrics and server control endpoints, returning `{ success: false, message, status: "error" }`.

---

For more details, see the Node-RED flow file: [`nodered/minecraft-stats-exporter.json`](../../nodered/minecraft-stats-exporter.json)
