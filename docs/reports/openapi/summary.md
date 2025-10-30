# OpenAPI Sync Result

**Status:** In sync ✅

_Diff color output: disabled (mode=auto, non-TTY)._

## Coverage Summary

| Metric | Value | Percent |
|--------|-------|---------|
| Handlers considered | 15 | - |
| Ignored handlers | 59 | - |
| With doc blocks | 15 | 100.0% |
| In swagger (handlers) | 15 | 100.0% |
| Definition matches | 15 / 15 | 100.0% |
| Swagger only operations | 42 | - |
| Model components generated | 36 | - |
| Schemas not generated | 0 | - |

## Suggestions

- Remove, implement, or ignore swagger-only operations.

## Swagger-only Operations (no handler)

- `GET /api/v1/guilds`
- `GET /api/v1/guilds/lookup/{guild_id}`
- `GET /api/v1/guilds/lookup/batch/{guild_ids}`
- `GET /api/v1/guilds/lookup/batch`
- `POST /api/v1/guilds/lookup/batch`
- `GET /api/v1/guild/{guild_id}/channel/{channel_id}/messages`
- `GET /api/v1/guild/{guild_id}/channel/{channel_id}/message/{message_id}`
- `POST /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/ids`
- `POST /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/reactions`
- `POST /api/v1/guild/{guild_id}/emojis/ids/batch`
- `POST /api/v1/guild/{guild_id}/emojis/names/batch`
- `GET /api/v1/guild/{guild_id}/roles`
- `POST /api/v1/guild/{guild_id}/roles/batch/ids`
- `GET /api/v1/guild/{guild_id}/join-whitelist`
- `POST /api/v1/guild/{guild_id}/join-whitelist`
- `GET /api/v1/guild/{guild_id}/join-whitelist/page`
- `PUT /api/v1/guild/{guild_id}/join-whitelist/{user_id}`
- `DELETE /api/v1/guild/{guild_id}/join-whitelist/{user_id}`
- `POST /api/v1/guild/{guild_id}/mentionables/batch/ids`
- `GET /api/v1/guild/{guild_id}/mentionables`
- `GET /api/v1/minecraft/whitelist.json`
- `GET /api/v1/minecraft/ops.json`
- `GET /api/v1/minecraft/uuid/{username}`
- `GET /api/v1/minecraft/status`
- `GET /api/v1/minecraft/version`
... and 17 more

## Ignored Endpoints (@openapi: ignore)

- `POST /webhook/minecraft/player/event` (MinecraftPlayerWebhookHandler.py:event)
- `POST /webhook/shift` (ShiftCodeWebhookHandler.py:shift_code)
- `POST /webhook/minecraft/tacos` (TacosWebhookHandler.py:minecraft_give_tacos)
- `POST /webhook/tacos` (TacosWebhookHandler.py:give_tacos)
- `POST /api/v1/guild/{guild_id}/emojis/ids/batch` (GuildEmojisApiHandler.py:get_guild_emojis_batch_by_ids)
- `POST /api/v1/guild/{guild_id}/emojis/names/batch` (GuildEmojisApiHandler.py:get_guild_emojis_batch_by_names)
- `GET /api/v1/guilds/lookup` (GuildLookupApiHandler.py:guild_lookup)
- `GET /api/v1/guilds/lookup/{guild_id}` (GuildLookupApiHandler.py:guild_lookup)
- `POST /api/v1/guilds/lookup` (GuildLookupApiHandler.py:guild_lookup)
- `GET /api/v1/guilds/lookup/batch` (GuildLookupApiHandler.py:guild_lookup_batch)
- `GET /api/v1/guilds/lookup/batch/{guild_ids}` (GuildLookupApiHandler.py:guild_lookup_batch)
- `POST /api/v1/guilds/lookup/batch` (GuildLookupApiHandler.py:guild_lookup_batch)
- `GET /api/v1/guilds` (GuildLookupApiHandler.py:get_guilds)
- `GET /api/v1/guild/{guild_id}/channel/{channel_id}/messages` (GuildMessagesApiHandler.py:get_channel_messages)
- `GET /api/v1/guild/{guild_id}/channel/{channel_id}/message/{message_id}` (GuildMessagesApiHandler.py:get_channel_message)
- `POST /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/ids` (GuildMessagesApiHandler.py:get_channel_messages_batch_by_ids)
- `POST /api/v1/guild/{guild_id}/channel/{channel_id}/messages/batch/reactions` (GuildMessagesApiHandler.py:get_reactions_for_messages_batch_by_ids)
- `GET /api/v1/guild/{guild_id}/roles` (GuildRolesApiHandler.py:get_guild_roles)
- `POST /api/v1/guild/{guild_id}/roles/batch/ids` (GuildRolesApiHandler.py:get_guild_roles_batch_by_ids)
- `POST /api/v1/guild/{guild_id}/mentionables/batch/ids` (GuildRolesApiHandler.py:get_guild_mentionables_batch_by_ids)
- `GET /api/v1/guild/{guild_id}/mentionables` (GuildRolesApiHandler.py:get_guild_mentionables)
- `GET /api/v1/guild/{guild_id}/join-whitelist` (JoinWhitelistApiHandler.py:list_join_whitelist)
- `GET /api/v1/guild/{guild_id}/join-whitelist/page` (JoinWhitelistApiHandler.py:list_join_whitelist_paged)
- `POST /api/v1/guild/{guild_id}/join-whitelist` (JoinWhitelistApiHandler.py:add_join_whitelist_user)
- `PUT /api/v1/guild/{guild_id}/join-whitelist/{user_id}` (JoinWhitelistApiHandler.py:update_join_whitelist_user)
- `DELETE /api/v1/guild/{guild_id}/join-whitelist/{user_id}` (JoinWhitelistApiHandler.py:delete_join_whitelist_user)
- `GET /api/v1/minecraft/whitelist.json` (MinecraftApiHandler.py:minecraft_whitelist)
- `GET /tacobot/minecraft/whitelist.json` (MinecraftApiHandler.py:minecraft_whitelist)
- `GET /taco/minecraft/whitelist.json` (MinecraftApiHandler.py:minecraft_whitelist)
- `GET /tacobot/minecraft/ops.json` (MinecraftApiHandler.py:minecraft_oplist)
- `GET /taco/minecraft/ops.json` (MinecraftApiHandler.py:minecraft_oplist)
- `GET /api/v1/minecraft/ops.json` (MinecraftApiHandler.py:minecraft_oplist)
- `GET /tacobot/minecraft/status` (MinecraftApiHandler.py:minecraft_server_status)
- `GET /taco/minecraft/status` (MinecraftApiHandler.py:minecraft_server_status)
- `GET /api/v1/minecraft/status` (MinecraftApiHandler.py:minecraft_server_status)
- `POST /tacobot/minecraft/version` (MinecraftApiHandler.py:minecraft_update_settings)
- `POST /taco/minecraft/version` (MinecraftApiHandler.py:minecraft_update_settings)
- `POST /api/v1/minecraft/version` (MinecraftApiHandler.py:minecraft_update_settings)
- `GET /tacobot/minecraft/version` (MinecraftApiHandler.py:minecraft_get_settings)
- `GET /taco/minecraft/version` (MinecraftApiHandler.py:minecraft_get_settings)
- `GET /api/v1/minecraft/version` (MinecraftApiHandler.py:minecraft_get_settings)
- `GET /tacobot/minecraft/player/events` (MinecraftApiHandler.py:minecraft_player_events)
- `GET /taco/minecraft/player/events` (MinecraftApiHandler.py:minecraft_player_events)
- `GET /api/v1/minecraft/player/events` (MinecraftApiHandler.py:minecraft_player_events)
- `GET /tacobot/minecraft/worlds` (MinecraftApiHandler.py:minecraft_worlds)
- `GET /taco/minecraft/worlds` (MinecraftApiHandler.py:minecraft_worlds)
- `GET /api/v1/minecraft/worlds` (MinecraftApiHandler.py:minecraft_worlds)
- `GET /tacobot/minecraft/world` (MinecraftApiHandler.py:minecraft_active_world)
- `GET /taco/minecraft/world` (MinecraftApiHandler.py:minecraft_active_world)
- `GET /api/v1/minecraft/world` (MinecraftApiHandler.py:minecraft_active_world)
... and 9 more
