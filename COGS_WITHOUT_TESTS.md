# TacoBot Cogs Without Unit Tests

This document lists all Discord cogs in the TacoBot project that do not yet have comprehensive unit tests defined.

## Summary

- **Total cogs found**: 44
- **Cogs with tests**: 26
- **Cogs without tests**: 18
- **Coverage**: ~59%

## Cogs Without Unit Tests

### Core Functionality

- `command_sync.py` - Discord command synchronization
- `events.py` - General event handling
- `guild_track.py` - Guild membership tracking

### Gaming & Entertainment

- `free_games.py` - Free game notifications
- `game_keys.py` - Game key distribution
- `giphy.py` - GIF integration
- `minecraft.py` - Minecraft server integration *(Note: Has basic test file but may need expansion)*
- `taco_tuesday.py` - Taco Tuesday game/event
- `tqotd.py` - "This or That" questions
- `trivia.py` - Trivia game system

### Social Features

- `introduction.py` - User introduction system
- `voicechat.py` - Voice channel management *(Note: Has basic test file but may need expansion)*

### Moderation & Administration

- `mod_events.py` - Moderator event logging *(Note: Has basic test file but may need expansion)*
- `move_message.py` - Message moving functionality *(Note: Has basic test file but may need expansion)*
- `new_account_check.py` - New account verification

### Utility & Miscellaneous

- `_amazon_links.py` - Amazon link processing (internal utility)
- `_leave_survey.py` - User departure surveys (internal utility)
- `_lfg.py` - "Looking for Group" functionality (internal utility)

## Cogs With Unit Tests ✅

### Core Features

- `account_link.py` - Account linking system
- `announcements.py` - Announcement system
- `assistant.py` - AI assistant integration
- `birthday.py` - Birthday tracking and notifications (84% coverage)
- `help.py` - Help command system
- `httphandler.py` - HTTP request handling

### Social & Community Features

- `invite_tracker.py` - Discord invite tracking
- `join_leave.py` - Join/leave message handling
- `live_now.py` - Live streaming notifications
- `mental_monday.py` - Mental health check-in system
- `message_preview.py` - Message preview functionality
- `message_track.py` - Message tracking
- `photo_post.py` - Photo posting system
- `server_event.py` - Server event handling
- `streamteam.py` - Stream team management
- `suggestions.py` - Suggestion system
- `tacopost.py` - Taco posting system
- `tacos.py` - Taco economy system
- `tech_thursday.py` - Tech sharing system
- `twitchinfo.py` - Twitch integration
- `user_lookup.py` - User lookup functionality
- `wdyctw.py` - "What Do You Call This Wednesday" game

### Moderation Features

- `restricted.py` - Restricted command handling

## Implementation Notes

- Some cogs marked as "without tests" may have basic test files that need expansion
- Test files are located in `tests/cogs/` directory
- Some cogs have test files in the root `tests/` directory (e.g., `test_assistant.py`)
- Coverage percentage is approximate based on file count comparison

## Development Priorities

### High Priority (Core functionality, frequently used)

1. `command_sync.py`
2. `events.py`
3. `guild_track.py`

### Medium Priority (Gaming features)

1. `taco_tuesday.py`
2. `trivia.py`
3. `tqotd.py`
4. `free_games.py`

### Low Priority (Specialized features)

1. `introduction.py`
2. `new_account_check.py`
3. `giphy.py`
4. `game_keys.py`
5. `_amazon_links.py`
6. `_leave_survey.py`
7. `_lfg.py`

## Testing Best Practices

When creating tests for these cogs, follow the established patterns from existing test files:

- Use shared fixtures from `conftest.py`
- Test both success and error paths
- Include permission checks
- Mock external dependencies (Discord API, databases, etc.)
- Aim for 80%+ code coverage
- Follow the naming convention: `test_<cog_name>.py`

## Notes

- Some cogs marked as "without tests" may have basic test files that need expansion
- Test files are located in `tests/cogs/` directory
- Some cogs have test files in the root `tests/` directory (e.g., `test_assistant.py`)
- Coverage percentage is approximate based on file count comparison

## Priority Recommendations

High Priority (Core functionality, frequently used):

1. `command_sync.py`
2. `events.py`
3. `guild_track.py`

Medium Priority (Gaming features):

1. `taco_tuesday.py`
2. `trivia.py`
3. `tqotd.py`
4. `free_games.py`

Low Priority (Specialized features):

1. `introduction.py`
2. `new_account_check.py`
3. `giphy.py`
4. `game_keys.py`
5. `_amazon_links.py`
6. `_leave_survey.py`
7. `_lfg.py`

## Testing Guidelines

When creating tests for these cogs, follow the established patterns from existing test files:

- Use shared fixtures from `conftest.py`
- Test both success and error paths
- Include permission checks
- Mock external dependencies (Discord API, databases, etc.)
- Aim for 80%+ code coverage
- Follow the naming convention: `test_<cog_name>.py`
