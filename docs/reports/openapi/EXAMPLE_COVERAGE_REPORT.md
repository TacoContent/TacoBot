# 📊 OpenAPI Coverage Report

## 📈 Coverage Summary

| Metric | Count | Coverage |
|--------|-------|----------|
| Handlers (considered) | 15 | - |
| Ignored | 59 | - |
| With OpenAPI block | 15 | 🟢 15/15 (100.0%) |
| In swagger | 15 | 🟢 15/15 (100.0%) |
| Definition matches | 15 | 🟢 15/15 (100.0%) |
| Swagger only operations | 42 | - |

## ✨ Documentation Quality Metrics

| Quality Indicator | Count | Rate |
|-------------------|-------|------|
| 📝 Summary | 15 | 🟢 15/15 (100.0%) |
| 📄 Description | 14 | 🟢 14/15 (93.3%) |
| 🔧 Parameters | 9 | 🟡 9/15 (60.0%) |
| 📦 Request body | 2 | 🔴 2/15 (13.3%) |
| 🔀 Multiple responses | 9 | 🟡 9/15 (60.0%) |
| 💡 Examples | 0 | 🔴 0/15 (0.0%) |

## 🔄 HTTP Method Breakdown

| Method | Total | Documented | In Swagger |
|--------|-------|------------|------------|
| 📖 GET | 13 | 🟢 13/13 (100.0%) | 13 |
| 📥 POST | 2 | 🟢 2/2 (100.0%) | 2 |

## 🏷️ Tag Coverage

**Unique tags:** 8

| Tag | Endpoints |
|-----|-----------|
| channels | 4 |
| emojis | 3 |
| guilds | 7 |
| health | 3 |
| permissions | 1 |
| settings | 1 |
| swagger | 2 |
| webhook | 1 |

## 📁 Top Files by Endpoint Count

| File | Total | Documented |
|------|-------|------------|
| GuildChannelsApiHandler.py | 4 | 🟢 4/4 (100.0%) |
| GuildEmojisApiHandler.py | 3 | 🟢 3/3 (100.0%) |
| HealthcheckApiHandler.py | 3 | 🟢 3/3 (100.0%) |
| SwaggerHttpHandler.py | 2 | 🟢 2/2 (100.0%) |
| FreeGameWebhookHandler.py | 1 | 🟢 1/1 (100.0%) |
| SettingsApiHandler.py | 1 | 🟢 1/1 (100.0%) |
| TacoPermissionsApiHandler.py | 1 | 🟢 1/1 (100.0%) |

## 📋 Per-Endpoint Details

### Documented Endpoints

- ✅ `POST /webhook/game`
- ✅ `GET /api/v1/guild/{guild_id}/categories`
- ✅ `GET /api/v1/guild/{guild_id}/category/{category_id}`
- ✅ `GET /api/v1/guild/{guild_id}/channels`
- ✅ `POST /api/v1/guild/{guild_id}/channels/batch/ids`
- ✅ `GET /api/v1/guild/{guild_id}/emojis`
- ✅ `GET /api/v1/guild/{guild_id}/emoji/id/{emoji_id}`
- ✅ `GET /api/v1/guild/{guild_id}/emoji/name/{emoji_name}`
- ✅ `GET /api/v1/health`
- ✅ `GET /healthz`
- ✅ `GET /health`
- ✅ `GET /api/v1/settings/{section}`
- ✅ `GET /swagger.yaml`
- ✅ `GET /api/v1/swagger.yaml`
- ✅ `GET /api/v1/permissions/{guildId}/{userId}`

### 🔍 Swagger-Only Operations

- ❌ `GET /api/v1/guilds`
- ❌ `GET /api/v1/guilds/lookup/{guild_id}`
- ❌ `GET /api/v1/guilds/lookup/batch/{guild_ids}`
- ❌ `GET /api/v1/guilds/lookup/batch`
- ❌ `POST /api/v1/guilds/lookup/batch`
- ❌ `GET /api/v1/guild/{guild_id}/channel/{channel_id}/messages`
- ❌ `GET /api/v1/guild/{guild_id}/channel/{channel_id}/message/{message_id}`
- ❌ `POST /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/ids`
- ❌ `POST /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/reactions`
- ❌ `POST /api/v1/guild/{guild_id}/emojis/ids/batch`
- ❌ `POST /api/v1/guild/{guild_id}/emojis/names/batch`
- ❌ `GET /api/v1/guild/{guild_id}/roles`
- ❌ `POST /api/v1/guild/{guild_id}/roles/batch/ids`
- ❌ `GET /api/v1/guild/{guild_id}/join-whitelist`
- ❌ `POST /api/v1/guild/{guild_id}/join-whitelist`
- ❌ `GET /api/v1/guild/{guild_id}/join-whitelist/page`
- ❌ `PUT /api/v1/guild/{guild_id}/join-whitelist/{user_id}`
- ❌ `DELETE /api/v1/guild/{guild_id}/join-whitelist/{user_id}`
- ❌ `POST /api/v1/guild/{guild_id}/mentionables/batch/ids`
- ❌ `GET /api/v1/guild/{guild_id}/mentionables`
- ❌ `GET /api/v1/minecraft/whitelist.json`
- ❌ `GET /api/v1/minecraft/ops.json`
- ❌ `GET /api/v1/minecraft/uuid/{username}`
- ❌ `GET /api/v1/minecraft/status`
- ❌ `GET /api/v1/minecraft/version`
- ❌ `POST /api/v1/minecraft/version`
- ❌ `GET /api/v1/minecraft/player/{user}/stats`
- ❌ `POST /api/v1/minecraft/player/{user}/stats`
- ❌ `GET /api/v1/minecraft/player/{username}/stats/{world}`
- ❌ `GET /api/v1/minecraft/world`
- ❌ `POST /api/v1/minecraft/world`
- ❌ `GET /api/v1/minecraft/worlds`
- ❌ `POST /tacobot/guild/{guild}/invite/{channel}`
- ❌ `GET /api/v1/minecraft/player/events`
- ❌ `GET /api/v1/minecraft/player/event/{event}`
- ❌ `POST /api/v1/permissions/{guildId}/{userId}/{permission}`
- ❌ `PUT /api/v1/permissions/{guildId}/{userId}/{permission}`
- ❌ `DELETE /api/v1/permissions/{guildId}/{userId}/{permission}`
- ❌ `POST /webhook/minecraft/tacos/{action}`
- ❌ `DELETE /webhook/minecraft/tacos/{action}`
- ❌ `POST /webhook/minecraft/player/event`
- ❌ `POST /webhook/shift`

