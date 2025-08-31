# Node-RED Flows: OurTacoBot

This documentation describes the available HTTP endpoints and the main flows defined in the `ourtacobot.json` Node-RED configuration.

## HTTP Endpoints

### POST `/tacobot/guild/:guild/invite/:channel`

- **Description:** Invite a channel to a Discord guild via TacoBot.
- **Method:** POST
- **Parameters:**
  - `guild`: Discord guild/server ID (URL parameter)
  - `channel`: Channel name (URL parameter)
- **Headers:**
  - `X-AUTH-TOKEN`: Required. Must match the configured value (`XXXXXXXXXXXXXXXXXXX`) [REDACTED].
- **Responses:**
  - `200 OK`: Invitation command triggered.
  - `403 Forbidden`: Invalid guild or auth token.

- **Example cURL:**

  ```sh
  curl -X POST \
    -H "X-AUTH-TOKEN: XXXXXXXXXXXXXXXXXXX" \
    http://<nodered-host>/tacobot/guild/935294040386183228/invite/darthminos
  ```

## Main Flows

### Twitch Event Flows

- **Join Channels:**
  - On `tmi-event-connected`, triggers a join for all bot channels from the `twitch_channels` MongoDB collection.
- **Host/Raid Events:**
  - On `tmi-event-hosted` or `tmi-event-raided`, builds and sends a `!taco host` or `!taco raid` command to the bot channel.
- **Cheer Events:**
  - On `tmi-event-cheer`, if bits >= 100, triggers a `!taco cheer` command.
- **Subscription Events:**
  - Handles new subscriptions, resubs, prime upgrades, subgifts, and gift upgrades, triggering a `!taco subscribe` command.

### GamerPower Free Game Key Flow

- **Manual/Beta/Production Triggers:**
  - Triggers a poll to `gamerpower.com/api/giveaways` for new free game keys.
  - Filters, formats, and stores new keys in the `free_game_keys` MongoDB collection.
  - Sends notifications via HTTP POST to configured endpoints.

### Error Handling

- **Catch Node:**
  - Captures errors in the GamerPower/game key flows and outputs to debug.

---

For more details, see the Node-RED flow file: [`nodered/ourtacobot.json`](../../nodered/ourtacobot.json)
