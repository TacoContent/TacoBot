# TACOBOT PROMETHEUS METRICS EXPORTER

## METRICS

| METRIC | DESCRIPTION | TYPE | LABELS |
| --- | --- | --- | --- |
| `tacobot_tacos` | The number of tacos given to users | `gauge` | `guild_id` |
| `tacobot_taco_gifts` | The number of tacos gifted to users | `gauge` | `guild_id` |
| `tacobot_taco_reactions` | The number of tacos given to users via reactions | `gauge` | `guild_id` |
| `tacobot_live_now` | The number of people currently live | `gauge` | `guild_id` |
| `tacobot_twitch_channels` | The number of twitch channels the bot is watching | `gauge` | `guild_id` |
| `tacobot_twitch_tacos` | The number of tacos given to twitch users | `gauge` | `guild_id` |
| `tacobot_twitch_linked_accounts` | The number of twitch accounts linked to discord accounts | `gauge` | *(none)* |
| `tacobot_tqotd` | The number of questions in the TQOTD database | `gauge` | `guild_id` |
| `tacobot_tqotd_answers` | The number of answers in the TQOTD database | `gauge` | `guild_id` |
| `tacobot_invited_users` | The number of users invited to the server | `gauge` | `guild_id` |
| `tacobot_live_platform` | The number of users that have gone live on a platform | `gauge` | `guild_id`, `platform` |
| `tacobot_wdyctw_questions` | The number of questions in the WDYCTW database | `gauge` | `guild_id` |
| `tacobot_wdyctw_answers` | The number of answers in the WDYCTW database | `gauge` | `guild_id` |
| `tacobot_techthurs` | The number of questions in the TechThurs database | `gauge` | `guild_id` |
| `tacobot_techthurs_answers` | The number of answers in the TechThurs database | `gauge` | `guild_id` |
| `tacobot_mentalmondays` | The number of questions in the MentalMondays database | `gauge` | `guild_id` |
| `tacobot_mentalmondays_answers` | The number of answers in the MentalMondays database | `gauge` | `guild_id` |
| `tacobot_tacotuesday` | The number of featured posts for TacoTuesday | `gauge` | `guild_id` |
| `tacobot_tacotuesday_answers` | The number of interactions in the TacoTuesday database | `gauge` | `guild_id` |
| `tacobot_game_keys_available` | The number of game keys available | `gauge` | `guild_id` |
| `tacobot_game_keys_redeemed` | The number of game keys claimed | `gauge` | `guild_id` |
| `tacobot_user_game_keys_redeemed` | The number of game keys claimed by a user | `gauge` | `guild_id`, `user_id`, `username` |
| `tacobot_user_game_keys_submitted` | The number of game keys submitted by a user | `gauge` | `guild_id`, `user_id`, `username` |
| `tacobot_minecraft_whitelist` | The number of users on the minecraft whitelist | `gauge` | `guild_id` |
| `tacobot_logs` | The number of logs | `gauge` | `guild_id`, `level` |
| `tacobot_team_requests` | The number of stream team requests | `gauge` | `guild_id` |
| `tacobot_birthdays` | The number of birthdays | `gauge` | `guild_id` |
| `tacobot_first_messages_today` | The number of first messages today | `gauge` | `guild_id` |
| `tacobot_known_users` | The number of known users | `gauge` | `guild_id`, `type` |
| `tacobot_messages` | The number of top messages | `gauge` | `guild_id`, `user_id`, `username` |
| `tacobot_gifters` | The number of top gifters | `gauge` | `guild_id`, `user_id`, `username` |
| `tacobot_reactors` | The number of top reactors | `gauge` | `guild_id`, `user_id`, `username` |
| `tacobot_top_tacos` | The number of top tacos | `gauge` | `guild_id`, `user_id`, `username` |
| `tacobot_taco_logs` | The number of taco logs | `gauge` | `guild_id`, `type` |
| `tacobot_live_activity` | The number of top live activity | `gauge` | `guild_id`, `user_id`, `username`, `platform` |
| `tacobot_suggestions` | The number of suggestions | `gauge` | `guild_id`, `status` |
| `tacobot_user_join_leave` | The number of users that have joined or left | `gauge` | `guild_id`, `action` |
| `tacobot_photo_posts` | The number of photo posts | `gauge` | `guild_id`, `user_id`, `username`, `channel` |
| `tacobot_guilds` | The number of guilds | `gauge` | `guild_id`, `name` |
| `tacobot_trivia_questions` | The number of trivia questions | `gauge` | `guild_id`, `difficulty`, `category`, `starter_id`, `starter_name` |
| `tacobot_trivia_answers` | The number of trivia answers | `gauge` | `guild_id`, `user_id`, `username`, `state` |
| `tacobot_invites` | The number of invites | `gauge` | `guild_id`, `user_id`, `username` |
| `tacobot_system_actions` | The number of system actions | `gauge` | `guild_id`, `action` |
| `tacobot_user_status` | The number of users with a status | `gauge` | `guild_id`, `status` |
| `tacobot_introductions` | The number of introductions | `gauge` | `guild_id`, `approved` |
| `tacobot_twitch_stream_avatar_duel_winners` | The number of twitch stream avatar duel winners | `gauge` | `guild_id`, `user_id`, `username`, `channel`, `channel_user_id` |
| `tacobot_free_game_keys` | The number of free game keys | `gauge` | `state` |
| `tacobot_permission` | The number of users that have the permission assigned | `gauge` | `guild_id`, `permission` |
| `tacobot_healthy` | The health of the bot | `gauge` | *(none)* |
| `tacobot_build_info` | A metric with a constant '1' value labeled with version | `gauge` | `version`, `ref`, `build_date`, `sha` |
| `tacobot_exporter_errors` | The number of errors encountered | `gauge` | `source` |

## DASHBOARD

![dashboard](https://i.imgur.com/rprBHRz.png)
![dashboard](https://i.imgur.com/rhCZ7Wd.png)
