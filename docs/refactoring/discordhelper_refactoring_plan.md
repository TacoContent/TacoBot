# DiscordHelper Refactoring Plan

## Executive Summary

The `DiscordHelper` class has grown to **over 800 lines** and contains **25+ methods** with diverse responsibilities. This plan breaks it down into **6 specialized classes** organized into logical groupings, improving testability, maintainability, and adherence to Single Responsibility Principle (SRP).

**Current Issues:**
- Single massive class handling entity fetching, taco operations, user prompts, message operations, and role management
- Difficult to test individual concerns in isolation
- Hard to locate methods (developers must scan 800+ lines)
- Violates SRP - one class doing too many things
- High coupling - changes to one area can affect unrelated areas

**Solution:**
Break into specialized helper classes with focused responsibilities, maintain backward compatibility during migration, and provide comprehensive test coverage.

---

## Current Class Analysis

### Method Categorization

The `DiscordHelper` class contains the following method groups:

#### 1. **Discord Entity Fetching** (5 methods)
- `get_or_fetch_user(userId)` - Fetch Discord user by ID
- `get_or_fetch_member(guildId, userId)` - Fetch guild member
- `get_or_fetch_role(guild, roleId)` - Fetch role from guild
- `get_or_fetch_channel(channelId)` - Fetch channel by ID
- `get_by_name_or_id(iterable, nameOrId)` - Generic lookup helper

#### 2. **User Interaction/Prompts** (8 methods)
- `ask_yes_no(...)` - Yes/No confirmation dialog
- `ask_channel(...)` - Channel selection prompt
- `ask_channel_by_name_or_id(...)` - Manual channel input
- `ask_number(...)` - Numeric input prompt
- `ask_text(...)` - Text input prompt
- `ask_for_image_or_text(...)` - Image or text input prompt
- `ask_role_list(...)` - Role selection prompt

#### 3. **Taco System Operations** (4 methods)
- `taco_give_user(...)` - Give tacos to user
- `taco_purge_log(...)` - Log taco purge event
- `tacos_log(...)` - Log taco transaction
- `_get_tacos_settings(guildId)` - Private helper for taco settings

#### 4. **Message Operations** (2 methods)
- `move_message(...)` - Move/copy message to different channel
- `notify_bot_not_initialized(...)` - Send initialization error message

#### 5. **Role Management** (1 method)
- `add_remove_roles(...)` - Bulk add/remove roles from user

#### 6. **Utility/Context** (1 method)
- `create_context(...)` - Create mock context object for testing

---

## Proposed New Architecture

### Directory Structure

```
bot/lib/helpers/
├── __init__.py                  # Exports all helper classes
├── entity_helper.py             # Discord entity fetching
├── prompt_helper.py             # User interaction prompts
├── taco_helper.py               # Taco system operations
├── message_helper.py            # Message operations
├── role_helper.py               # Role management
└── context_helper.py            # Context creation utilities
```

### New Classes Overview

#### 1. `EntityHelper` (entity_helper.py)
**Responsibility:** Fetch and retrieve Discord entities (users, members, roles, channels)

**Methods:**
- `get_or_fetch_user(userId: int) -> discord.User | None`
- `get_or_fetch_member(guildId: int, userId: int) -> discord.Member | None`
- `get_or_fetch_role(guild: discord.Guild, roleId: int) -> discord.Role | None`
- `get_or_fetch_channel(channelId: int) -> discord.TextChannel | discord.DMChannel | discord.Thread | None`
- `get_by_name_or_id(iterable, nameOrId: int | str) -> Any | None`

**Dependencies:**
- `discord` library
- `logger.Log`
- Bot instance (for API calls)

**Testing Strategy:**
- Mock bot.get_user/fetch_user responses
- Test NotFound error handling
- Test None/invalid ID handling
- Test cache vs fetch behavior

---

#### 2. `PromptHelper` (prompt_helper.py)
**Responsibility:** Handle all user interaction prompts and input collection

**Methods:**
- `ask_yes_no(ctx, targetChannel, question, title, timeout, ...) -> None`
- `ask_channel(ctx, title, message, allow_none, timeout, callback) -> None`
- `ask_channel_by_name_or_id(ctx, title, description, timeout) -> discord.Channel | None`
- `ask_number(ctx, title, message, min_value, max_value, timeout) -> int | None`
- `ask_text(ctx, targetChannel, title, message, timeout, color) -> str | None`
- `ask_for_image_or_text(ctx, targetChannel, title, message, timeout, color) -> TextWithAttachments | None`
- `ask_role_list(ctx, title, message, allow_none, exclude_roles, timeout, select_callback) -> discord.Role | None`

**Dependencies:**
- `Messaging` (for sending embeds)
- `EntityHelper` (for entity lookups)
- `Settings` (for i18n strings)
- View classes (YesOrNoView, ChannelSelectView, RoleSelectView)
- Bot instance (for wait_for)

**Testing Strategy:**
- Mock bot.wait_for with controlled timeout
- Mock messaging.send_embed
- Test callback invocation
- Test timeout handling
- Test user message cleanup
- Test DM vs guild channel behavior

---

#### 3. `TacoHelper` (taco_helper.py)
**Responsibility:** Handle taco giving, logging, and taco-related operations

**Methods:**
- `give_tacos(guildId, fromUser, toUser, reason, give_type, taco_amount) -> int`
- `log_taco_transaction(guild_id, toMember, fromMember, count, total_tacos, reason, type) -> None`
- `log_taco_purge(guild_id, toMember, fromMember, reason) -> None`
- `get_taco_settings(guildId) -> dict`

**Dependencies:**
- `TacosDatabase` (for taco persistence)
- `EntityHelper` (for channel fetching)
- `Messaging` (for log channel messages)
- `Settings` (for i18n and taco settings)
- `utils` (for user display names)

**Testing Strategy:**
- Mock TacosDatabase.add_tacos
- Mock TacosDatabase.track_tacos_log
- Test taco amount calculation from settings
- Test log channel message formatting
- Test plural/singular taco word logic
- Test negative taco counts (loss vs received)

---

#### 4. `MessageHelper` (message_helper.py)
**Responsibility:** Message manipulation and bot notification messages

**Methods:**
- `move_message(message, targetChannel, author, who, reason, fields, remove_fields, color, delete_original) -> discord.Message | None`
- `notify_bot_not_initialized(ctx, subcommand) -> None`

**Dependencies:**
- `Messaging` (for sending embeds)
- `Settings` (for i18n strings)
- `utils` (for user display names)

**Testing Strategy:**
- Mock message.embeds and attachments
- Test embed field merging/removal logic
- Test image attachment handling
- Test footer generation
- Test delete_original flag
- Mock ctx.author.guild_permissions.administrator

---

#### 5. `RoleHelper` (role_helper.py)
**Responsibility:** Role addition and removal operations

**Methods:**
- `add_remove_roles(user, check_list, add_list, remove_list, allow_everyone) -> None`

**Dependencies:**
- `logger.Log`
- Discord member/guild objects

**Testing Strategy:**
- Mock user.roles collection
- Mock user.add_roles and user.remove_roles
- Test check_list filtering logic
- Test allow_everyone bypass
- Test exception handling during role operations
- Test logging of role changes

---

#### 6. `ContextHelper` (context_helper.py)
**Responsibility:** Create mock/test context objects

**Methods:**
- `create_context(bot, author, guild, channel, message, invoked_subcommand, **kwargs) -> namedtuple`

**Dependencies:**
- `collections.namedtuple`

**Testing Strategy:**
- Test all standard parameters
- Test **kwargs merging
- Test returned object has correct attributes
- Test with None values

---

## Backward Compatibility Layer

To maintain compatibility during migration, we'll create a **facade/wrapper** that delegates to the new helpers:

### `DiscordHelper` (Deprecated - Legacy Facade)

```python
# bot/lib/discordhelper.py
from bot.lib.helpers import (
    EntityHelper,
    PromptHelper,
    TacoHelper,
    MessageHelper,
    RoleHelper,
    ContextHelper
)

class DiscordHelper:
    """
    DEPRECATED: This class is maintained for backward compatibility.
    New code should use the specialized helper classes:
    - EntityHelper: Discord entity fetching
    - PromptHelper: User interaction prompts
    - TacoHelper: Taco system operations
    - MessageHelper: Message operations
    - RoleHelper: Role management
    - ContextHelper: Context utilities
    """
    
    def __init__(self, bot):
        self.bot = bot
        # Initialize all helpers
        self.entity_helper = EntityHelper(bot)
        self.prompt_helper = PromptHelper(bot)
        self.taco_helper = TacoHelper(bot)
        self.message_helper = MessageHelper(bot)
        self.role_helper = RoleHelper(bot)
        self.context_helper = ContextHelper()
        
        # Legacy properties for backward compatibility
        self.settings = self.taco_helper.settings
        self.log = self.entity_helper.log
        self.messaging = self.message_helper.messaging
        self.tacos_db = self.taco_helper.tacos_db
    
    # Delegate all methods to appropriate helpers
    async def get_or_fetch_user(self, userId: int):
        return await self.entity_helper.get_or_fetch_user(userId)
    
    async def ask_yes_no(self, ctx, targetChannel, question, **kwargs):
        return await self.prompt_helper.ask_yes_no(ctx, targetChannel, question, **kwargs)
    
    async def taco_give_user(self, guildId, fromUser, toUser, reason, give_type, taco_amount):
        return await self.taco_helper.give_tacos(guildId, fromUser, toUser, reason, give_type, taco_amount)
    
    # ... (all other method delegations)
```

This allows **existing code to continue working** while we incrementally migrate to the new helpers.

---

## Migration Phases

### **Phase 1: Foundation & Infrastructure** (Week 1)
**Goal:** Set up new class structure with tests, no breaking changes

#### Tasks:
1. ✅ **Create directory structure**
   - Create `bot/lib/helpers/` directory
   - Create `__init__.py` with placeholder exports

2. ✅ **Create ContextHelper** (simplest, no dependencies)
   - File: `bot/lib/helpers/context_helper.py`
   - Extract `create_context` method
   - Add comprehensive tests in `tests/lib/helpers/test_context_helper.py`
   - Test namedtuple creation, **kwargs merging, None handling

3. ✅ **Create EntityHelper**
   - File: `bot/lib/helpers/entity_helper.py`
   - Extract all 5 entity fetching methods
   - Add tests in `tests/lib/helpers/test_entity_helper.py`
   - Mock bot responses, test NotFound handling, test None IDs

4. ✅ **Create RoleHelper** (simple, minimal dependencies)
   - File: `bot/lib/helpers/role_helper.py`
   - Extract `add_remove_roles` method
   - Add tests in `tests/lib/helpers/test_role_helper.py`
   - Mock role operations, test check_list logic

5. ✅ **Update `bot/lib/helpers/__init__.py`**
   ```python
   from .context_helper import ContextHelper
   from .entity_helper import EntityHelper
   from .role_helper import RoleHelper
   
   __all__ = ['ContextHelper', 'EntityHelper', 'RoleHelper']
   ```

**Deliverables:**
- 3 new helper classes with full test coverage
- All tests passing
- No changes to existing code yet

**Success Criteria:**
- 100% test coverage on new helpers
- All CI checks pass
- Documentation complete for Phase 1 classes

---

### **Phase 2: Message & Taco Helpers** (Week 2)
**Goal:** Extract message and taco operations

#### Tasks:
1. ✅ **Create MessageHelper**
   - File: `bot/lib/helpers/message_helper.py`
   - Extract `move_message` and `notify_bot_not_initialized`
   - Inject `Messaging` and `Settings` dependencies
   - Add tests in `tests/lib/helpers/test_message_helper.py`
   - Test embed merging, field removal, attachment handling

2. ✅ **Create TacoHelper**
   - File: `bot/lib/helpers/taco_helper.py`
   - Extract `taco_give_user`, `tacos_log`, `taco_purge_log`, `_get_tacos_settings`
   - Inject `TacosDatabase`, `EntityHelper`, `Messaging`, `Settings` dependencies
   - Rename methods: `taco_give_user` → `give_tacos`, `tacos_log` → `log_taco_transaction`
   - Add tests in `tests/lib/helpers/test_taco_helper.py`
   - Mock database operations, test plural/singular logic

3. ✅ **Update `bot/lib/helpers/__init__.py`**
   ```python
   from .context_helper import ContextHelper
   from .entity_helper import EntityHelper
   from .role_helper import RoleHelper
   from .message_helper import MessageHelper
   from .taco_helper import TacoHelper
   
   __all__ = ['ContextHelper', 'EntityHelper', 'RoleHelper', 'MessageHelper', 'TacoHelper']
   ```

**Deliverables:**
- 2 additional helper classes with full test coverage
- All tests passing
- No breaking changes yet

**Success Criteria:**
- 100% test coverage on MessageHelper and TacoHelper
- All CI checks pass
- Documentation updated

---

### **Phase 3: Prompt Helper** (Week 3)
**Goal:** Extract complex user interaction logic

#### Tasks:
1. ✅ **Create PromptHelper**
   - File: `bot/lib/helpers/prompt_helper.py`
   - Extract all 7 `ask_*` methods
   - Inject `Messaging`, `EntityHelper`, `Settings`, Bot dependencies
   - Add tests in `tests/lib/helpers/test_prompt_helper.py`
   - Mock bot.wait_for, test timeout handling, test callbacks

2. ✅ **Handle View dependencies**
   - Import `YesOrNoView`, `ChannelSelectView`, `RoleSelectView`
   - Keep view logic intact, only extract prompt orchestration

3. ✅ **Update `bot/lib/helpers/__init__.py`**
   ```python
   from .context_helper import ContextHelper
   from .entity_helper import EntityHelper
   from .role_helper import RoleHelper
   from .message_helper import MessageHelper
   from .taco_helper import TacoHelper
   from .prompt_helper import PromptHelper
   
   __all__ = [
       'ContextHelper',
       'EntityHelper', 
       'RoleHelper',
       'MessageHelper',
       'TacoHelper',
       'PromptHelper'
   ]
   ```

**Deliverables:**
- PromptHelper with full test coverage
- All 6 helper classes complete
- All tests passing

**Success Criteria:**
- 100% test coverage on PromptHelper
- All CI checks pass
- Documentation complete for all helpers

---

### **Phase 4: Backward Compatibility Facade** (Week 4)
**Goal:** Create delegation layer for existing code

#### Tasks:
1. ✅ **Create legacy DiscordHelper facade**
   - Modify `bot/lib/discordhelper.py`
   - Initialize all 6 helpers in `__init__`
   - Create delegation methods for all public methods
   - Add deprecation warnings to docstrings
   - Keep existing imports working

2. ✅ **Add integration tests**
   - Test that DiscordHelper still works as before
   - File: `tests/lib/test_discordhelper_facade.py`
   - Verify all methods delegate correctly
   - Ensure properties (settings, log, messaging, tacos_db) still accessible

3. ✅ **Update documentation**
   - Add migration guide: `docs/refactoring/discordhelper_migration_guide.md`
   - Document each helper's purpose and usage
   - Provide before/after code examples
   - Add deprecation notices to original DiscordHelper docstrings

**Deliverables:**
- Fully functional backward-compatible facade
- Integration tests passing
- Migration guide documentation

**Success Criteria:**
- All existing code works without changes
- All tests passing (old + new)
- CI pipeline green
- No breaking changes

---

### **Phase 5: Incremental Migration - Cogs** (Weeks 5-7)
**Goal:** Migrate cogs to use new helpers directly

**Migration Priority Order:**
1. **Low complexity cogs** (1-2 helper calls)
2. **Medium complexity cogs** (3-5 helper calls)
3. **High complexity cogs** (6+ helper calls)

#### Migration Template:

**Before:**
```python
from bot.lib import discordhelper

class MyCog:
    def __init__(self, bot):
        self.bot = bot
        self.discord_helper = discordhelper.DiscordHelper(bot)
    
    async def my_command(self, ctx):
        user = await self.discord_helper.get_or_fetch_user(123)
        await self.discord_helper.taco_give_user(...)
```

**After:**
```python
from bot.lib.helpers import EntityHelper, TacoHelper

class MyCog:
    def __init__(self, bot):
        self.bot = bot
        self.entity_helper = EntityHelper(bot)
        self.taco_helper = TacoHelper(bot)
    
    async def my_command(self, ctx):
        user = await self.entity_helper.get_or_fetch_user(123)
        await self.taco_helper.give_tacos(...)
```

#### Tasks per Cog:
1. ✅ Identify which helpers are needed
2. ✅ Replace `discordhelper.DiscordHelper` import with specific helpers
3. ✅ Update initialization to use new helpers
4. ✅ Update method calls (handle any renamed methods)
5. ✅ Run tests for that cog
6. ✅ Update any cog-specific documentation

#### Cog Migration Order:

**Week 5: Low Complexity (10-12 cogs)**
- `guild_track.py` (EntityHelper only)
- `message_track.py` (EntityHelper only)
- `voicechat.py` (EntityHelper only)
- `command_sync.py` (EntityHelper only)
- `free_games.py` (EntityHelper, MessageHelper)
- `giphy.py` (EntityHelper, PromptHelper)
- `photo_post.py` (EntityHelper, PromptHelper)
- `twitter_preview.py` (EntityHelper)
- `message_preview.py` (EntityHelper)
- `_amazon_links.py` (EntityHelper)

**Week 6: Medium Complexity (10-12 cogs)**
- `join_leave.py` (EntityHelper, MessageHelper, TacoHelper)
- `birthday.py` (EntityHelper, PromptHelper, TacoHelper)
- `introduction.py` (EntityHelper, PromptHelper)
- `invite_tracker.py` (EntityHelper, TacoHelper)
- `restricted.py` (EntityHelper, RoleHelper)
- `server_event.py` (EntityHelper, PromptHelper)
- `streamteam.py` (EntityHelper, PromptHelper, RoleHelper)
- `wdyctw.py` (EntityHelper, PromptHelper)
- `account_link.py` (EntityHelper, PromptHelper)
- `game_keys.py` (EntityHelper, PromptHelper)
- `_lfg.py` (EntityHelper, PromptHelper)

**Week 7: High Complexity (remaining cogs)**
- `tacos.py` (All helpers)
- `announcements.py` (EntityHelper, PromptHelper, MessageHelper)
- `suggestions.py` (EntityHelper, PromptHelper, MessageHelper)
- `move_message.py` (EntityHelper, MessageHelper)
- `minecraft.py` (EntityHelper, PromptHelper, TacoHelper)
- `new_account_check.py` (EntityHelper, RoleHelper, MessageHelper)
- `live_now.py` (EntityHelper, PromptHelper, TacoHelper)
- `taco_tuesday.py` (EntityHelper, PromptHelper, TacoHelper)
- `tech_thursday.py` (EntityHelper, PromptHelper, TacoHelper)
- `mental_monday.py` (EntityHelper, PromptHelper, TacoHelper)
- `tqotd.py` (EntityHelper, PromptHelper, TacoHelper)
- `trivia.py` (EntityHelper, PromptHelper, TacoHelper)
- `twitchinfo.py` (EntityHelper, PromptHelper)
- `user_lookup.py` (EntityHelper, PromptHelper)
- `tacopost.py` (EntityHelper, TacoHelper)
- `help.py` (EntityHelper, PromptHelper)
- `_leave_survey.py` (EntityHelper, PromptHelper)

**Deliverables per Week:**
- 10-12 cogs migrated
- All cog tests passing
- Documentation updated for migrated cogs

**Success Criteria per Week:**
- No functionality regression
- All tests passing
- CI pipeline green

---

### **Phase 6: HTTP Handler Migration** (Week 8)
**Goal:** Migrate HTTP API handlers and webhook handlers

#### Tasks:
1. ✅ **Migrate Base Handlers**
   - `BaseHttpHandler.py`
   - `ApiHttpHandler.py`
   - `BaseWebhookHandler.py`
   - Update constructors to inject specific helpers

2. ✅ **Migrate API v1 Handlers** (15+ handlers)
   - `GuildRolesApiHandler.py`
   - `GuildMessagesApiHandler.py`
   - `GuildLookupApiHandler.py`
   - `GuildEmojisApiHandler.py`
   - `GuildChannelsApiHandler.py`
   - `HealthcheckApiHandler.py`
   - `MinecraftApiHandler.py`
   - `JoinWhitelistApiHandler.py`
   - `SettingsApiHandler.py`
   - `SwaggerHttpHandler.py`
   - `TacoPermissionsApiHandler.py`

3. ✅ **Migrate Webhook Handlers**
   - `MinecraftPlayerWebhookHandler.py`
   - `ShiftCodeWebhookHandler.py`
   - `GuildResolver.py` (helper for webhooks)

4. ✅ **Update httphandler cog**
   - `bot/cogs/httphandler.py`

**Migration Pattern for Handlers:**

**Before:**
```python
from bot.lib import discordhelper

class MyApiHandler(BaseHttpHandler):
    def __init__(self, bot, discord_helper=None):
        super().__init__(bot)
        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)
```

**After:**
```python
from bot.lib.helpers import EntityHelper, MessageHelper

class MyApiHandler(BaseHttpHandler):
    def __init__(self, bot, entity_helper=None, message_helper=None):
        super().__init__(bot)
        self.entity_helper = entity_helper or EntityHelper(bot)
        self.message_helper = message_helper or MessageHelper(bot)
```

**Deliverables:**
- All HTTP handlers migrated
- All webhook handlers migrated
- API tests passing
- Swagger sync still works

**Success Criteria:**
- All API endpoints functional
- All webhook handlers functional
- HTTP integration tests passing
- CI pipeline green

---

### **Phase 7: Migration of Permissions & Utilities** (Week 9)
**Goal:** Migrate cross-cutting concerns

#### Tasks:
1. ✅ **Migrate bot/lib/permissions.py**
   - Currently uses DiscordHelper
   - Switch to EntityHelper only (for get_or_fetch_member)
   - Update tests

2. ✅ **Check for other lib utilities using DiscordHelper**
   - Search `bot/lib/` for any other files
   - Migrate as needed

3. ✅ **Run full integration test suite**
   - All unit tests
   - All integration tests
   - All API tests
   - All cog tests

**Deliverables:**
- All library utilities migrated
- Full test suite passing

**Success Criteria:**
- 100% of non-facade code using new helpers
- All tests passing
- CI pipeline green

---

### **Phase 8: Cleanup & Deprecation** (Week 10)
**Goal:** Mark facade as deprecated, prepare for eventual removal

#### Tasks:
1. ✅ **Add deprecation warnings to DiscordHelper facade**
   ```python
   import warnings
   
   class DiscordHelper:
       def __init__(self, bot):
           warnings.warn(
               "DiscordHelper is deprecated. Use specialized helpers instead:\n"
               "  EntityHelper, PromptHelper, TacoHelper, MessageHelper, RoleHelper, ContextHelper",
               DeprecationWarning,
               stacklevel=2
           )
           # ... rest of init
   ```

2. ✅ **Update all documentation**
   - README.md: Add note about new helpers
   - API documentation: Document new helpers
   - Migration guide: Complete with all examples
   - Add "See also" links between helper docs

3. ✅ **Create deprecation timeline**
   - Document when facade will be removed (e.g., 6 months, 1 year)
   - Add to changelog
   - Add to project roadmap

4. ✅ **Final test run**
   - Run full test suite with coverage
   - Ensure 80%+ coverage maintained
   - Run linters and formatters
   - Run swagger sync check

5. ✅ **Create PR for review**
   - Detailed description of changes
   - Link to this refactoring plan
   - Highlight test coverage improvements
   - Note no breaking changes for existing code

**Deliverables:**
- Complete refactoring with deprecation warnings
- Full documentation
- Deprecation timeline
- PR ready for review

**Success Criteria:**
- All tests passing
- 80%+ test coverage
- All CI checks passing
- Documentation complete
- PR approved

---

### **Phase 9: Future Removal (Optional - 6-12 months later)**
**Goal:** Remove deprecated facade after migration period

#### Tasks:
1. ⚠️ **Remove DiscordHelper facade**
   - Delete `bot/lib/discordhelper.py`
   - Remove from all imports (should be none if migration complete)

2. ⚠️ **Update all imports to helpers explicitly**
   - Final search for any remaining references
   - Update if any found

3. ⚠️ **Update documentation**
   - Remove all DiscordHelper references
   - Update examples

**Deliverables:**
- Clean codebase with no deprecated code
- Final documentation update

**Success Criteria:**
- No references to DiscordHelper remain
- All tests passing
- CI pipeline green

---

## Testing Strategy

### Test Coverage Requirements

- **Minimum coverage per helper:** 80%
- **Overall project coverage:** Maintain current coverage or improve
- **Critical paths:** 100% coverage (taco transactions, role operations, message moves)

### Test Types

#### 1. **Unit Tests** (per helper class)
- Mock all external dependencies (bot, database, messaging)
- Test each method in isolation
- Test error paths and edge cases
- Test None/invalid input handling

**Example:** `test_entity_helper.py`
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.lib.helpers import EntityHelper

@pytest.mark.asyncio
async def test_get_or_fetch_user_cache_hit():
    # Mock bot with cached user
    bot = MagicMock()
    user = MagicMock()
    user.id = 123
    bot.get_user.return_value = user
    
    helper = EntityHelper(bot)
    result = await helper.get_or_fetch_user(123)
    
    assert result == user
    bot.get_user.assert_called_once_with(123)
    bot.fetch_user.assert_not_called()

@pytest.mark.asyncio
async def test_get_or_fetch_user_cache_miss():
    # Mock bot with cache miss, fetch succeeds
    bot = MagicMock()
    user = MagicMock()
    bot.get_user.return_value = None
    bot.fetch_user = AsyncMock(return_value=user)
    
    helper = EntityHelper(bot)
    result = await helper.get_or_fetch_user(123)
    
    assert result == user
    bot.fetch_user.assert_called_once_with(123)

@pytest.mark.asyncio
async def test_get_or_fetch_user_not_found():
    # Mock bot with user not found
    bot = MagicMock()
    bot.get_user.return_value = None
    bot.fetch_user = AsyncMock(side_effect=discord.errors.NotFound(MagicMock(), MagicMock()))
    
    helper = EntityHelper(bot)
    result = await helper.get_or_fetch_user(123)
    
    assert result is None
```

#### 2. **Integration Tests** (facade)
- Test that DiscordHelper facade correctly delegates to helpers
- Verify backward compatibility
- Test property access (settings, log, messaging, tacos_db)

**Example:** `test_discordhelper_facade.py`
```python
@pytest.mark.asyncio
async def test_facade_delegates_get_or_fetch_user():
    bot = MagicMock()
    facade = DiscordHelper(bot)
    
    # Mock the underlying helper
    user = MagicMock()
    facade.entity_helper.get_or_fetch_user = AsyncMock(return_value=user)
    
    result = await facade.get_or_fetch_user(123)
    
    assert result == user
    facade.entity_helper.get_or_fetch_user.assert_called_once_with(123)

def test_facade_exposes_legacy_properties():
    bot = MagicMock()
    facade = DiscordHelper(bot)
    
    assert facade.settings is not None
    assert facade.log is not None
    assert facade.messaging is not None
    assert facade.tacos_db is not None
```

#### 3. **Regression Tests**
- Run existing DiscordHelper tests against facade
- Ensure no functionality lost
- Compare outputs before/after refactoring

#### 4. **Performance Tests** (optional but recommended)
- Measure method call overhead
- Ensure delegation doesn't significantly impact performance
- Benchmark entity fetching with cache vs fetch

### Test Organization

```
tests/
├── lib/
│   ├── helpers/
│   │   ├── test_context_helper.py        # ContextHelper tests
│   │   ├── test_entity_helper.py         # EntityHelper tests
│   │   ├── test_role_helper.py           # RoleHelper tests
│   │   ├── test_message_helper.py        # MessageHelper tests
│   │   ├── test_taco_helper.py           # TacoHelper tests
│   │   └── test_prompt_helper.py         # PromptHelper tests
│   ├── test_discordhelper_facade.py      # Facade integration tests
│   └── test_discordhelper_regression.py  # Regression tests (optional)
```

---

## Risk Mitigation

### Identified Risks

#### 1. **Breaking Changes During Migration**
**Risk Level:** HIGH  
**Impact:** Existing functionality stops working

**Mitigation:**
- Maintain facade for backward compatibility
- Extensive integration tests
- Incremental migration by phase
- Each phase tested independently
- No changes to public APIs during Phases 1-4

#### 2. **Test Coverage Drops**
**Risk Level:** MEDIUM  
**Impact:** Less confidence in refactored code

**Mitigation:**
- Require 80% coverage per helper before proceeding
- Run coverage reports after each phase
- Add tests for uncovered edge cases discovered during refactoring

#### 3. **Performance Regression**
**Risk Level:** LOW  
**Impact:** Method calls slower due to delegation overhead

**Mitigation:**
- Benchmark critical paths (entity fetching, taco transactions)
- Delegation is negligible overhead (simple method call)
- Most time spent in Discord API calls, not helper logic
- If needed, optimize hot paths in Phase 8

#### 4. **Incomplete Migration**
**Risk Level:** MEDIUM  
**Impact:** Some code still using facade indefinitely

**Mitigation:**
- Track migration progress per phase
- Checklist for each cog/handler
- Deprecation warnings in facade
- Scheduled facade removal in Phase 9

#### 5. **Increased Complexity in Tests**
**Risk Level:** LOW  
**Impact:** Tests need to mock more dependencies

**Mitigation:**
- Create shared test fixtures/mocks
- Document testing patterns in migration guide
- Provide example test files for each helper type

#### 6. **Circular Dependencies**
**Risk Level:** LOW  
**Impact:** Helpers depend on each other, creating import cycles

**Mitigation:**
- Design dependencies carefully (documented in "New Classes Overview")
- PromptHelper depends on EntityHelper (acceptable, one-way)
- TacoHelper depends on EntityHelper (acceptable, one-way)
- No helper should depend on facade
- Use dependency injection to break cycles if needed

---

## Documentation Updates

### Files to Create

1. **`docs/refactoring/discordhelper_refactoring_plan.md`** (this file)
   - Complete refactoring plan

2. **`docs/refactoring/discordhelper_migration_guide.md`**
   - Developer guide for migrating code
   - Before/after examples for each helper
   - Common migration patterns
   - FAQ section

3. **`docs/lib/helpers/README.md`**
   - Overview of all helpers
   - When to use which helper
   - Quick reference guide

4. **`docs/lib/helpers/entity_helper.md`**
   - EntityHelper API documentation
   - Usage examples
   - Testing guide

5. **`docs/lib/helpers/prompt_helper.md`**
   - PromptHelper API documentation
   - View integration patterns
   - Timeout handling best practices

6. **`docs/lib/helpers/taco_helper.md`**
   - TacoHelper API documentation
   - Taco settings configuration
   - Logging examples

7. **`docs/lib/helpers/message_helper.md`**
   - MessageHelper API documentation
   - Message move examples
   - Embed manipulation patterns

8. **`docs/lib/helpers/role_helper.md`**
   - RoleHelper API documentation
   - Bulk role operation examples
   - Permission considerations

9. **`docs/lib/helpers/context_helper.md`**
   - ContextHelper API documentation
   - Test context creation examples

### Files to Update

1. **`README.md`**
   - Add note about new helper structure
   - Link to migration guide
   - Update architecture section

2. **`docs/http/README.md`** (if exists)
   - Update handler base class examples

3. **`.github/copilot-instructions.md`**
   - Update with new helper patterns
   - Add section on when to use which helper
   - Deprecate DiscordHelper usage guidance

4. **`CHANGELOG.md`**
   - Document refactoring changes per phase
   - Note deprecation of DiscordHelper facade

---

## Success Metrics

### Quantitative Metrics

1. **Code Organization**
   - ✅ DiscordHelper reduced from 800+ lines to <100 lines (facade only)
   - ✅ 6 focused helper classes, each <200 lines
   - ✅ Average method count per class: <10 methods

2. **Test Coverage**
   - ✅ Overall project coverage maintained or improved (>80%)
   - ✅ Each helper has >80% coverage
   - ✅ Critical paths (tacos, roles, messages) have 100% coverage

3. **Maintainability**
   - ✅ Single Responsibility Principle adhered to
   - ✅ Each helper testable in isolation
   - ✅ Clear naming conventions (EntityHelper, PromptHelper, etc.)

4. **Migration Completeness**
   - ✅ 100% of cogs migrated to new helpers
   - ✅ 100% of HTTP handlers migrated
   - ✅ 100% of lib utilities migrated
   - ✅ 0 direct usages of DiscordHelper (except facade tests)

### Qualitative Metrics

1. **Developer Experience**
   - ✅ Easier to find relevant helper method (no scanning 800 lines)
   - ✅ Clearer what each helper is responsible for
   - ✅ Easier to mock dependencies in tests
   - ✅ Improved code documentation

2. **Code Quality**
   - ✅ Reduced coupling between concerns
   - ✅ Improved testability
   - ✅ Better adherence to SOLID principles
   - ✅ Cleaner dependency injection

3. **Team Productivity**
   - ✅ Faster onboarding (clearer structure)
   - ✅ Easier code reviews (smaller, focused PRs per phase)
   - ✅ Reduced merge conflicts (smaller files)

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1: Foundation | 1 week | ContextHelper, EntityHelper, RoleHelper + tests |
| Phase 2: Message & Taco | 1 week | MessageHelper, TacoHelper + tests |
| Phase 3: Prompt Helper | 1 week | PromptHelper + tests |
| Phase 4: Facade | 1 week | Backward-compatible facade + integration tests |
| Phase 5: Cog Migration | 3 weeks | All cogs using new helpers |
| Phase 6: HTTP Migration | 1 week | All HTTP handlers using new helpers |
| Phase 7: Lib Migration | 1 week | All lib utilities using new helpers |
| Phase 8: Cleanup | 1 week | Documentation, deprecation, PR |
| **Total** | **10 weeks** | Complete refactoring with no breaking changes |

**Optional Phase 9** (6-12 months later): Remove deprecated facade entirely

---

## Approval Checklist

Before proceeding with implementation, ensure:

- [ ] **Plan reviewed and approved** by project maintainer
- [ ] **Timeline is acceptable** (10 weeks)
- [ ] **Test coverage requirements agreed upon** (80% per helper, 100% critical paths)
- [ ] **Migration phases make sense** (can be adjusted if needed)
- [ ] **Backward compatibility approach approved** (facade pattern)
- [ ] **Documentation structure approved**
- [ ] **Success metrics are clear** and measurable
- [ ] **Risk mitigation strategies accepted**
- [ ] **Team has capacity** for 10-week refactoring
- [ ] **CI/CD pipeline ready** to run tests after each phase

---

## Next Steps After Approval

1. **Create tracking issue** with all phases as subtasks
2. **Set up project board** with phase columns
3. **Create branch**: `refactor/discordhelper-breakdown`
4. **Begin Phase 1**: Create `bot/lib/helpers/` directory
5. **Create tests for ContextHelper** before implementation
6. **Implement ContextHelper** and verify tests pass
7. **Repeat for EntityHelper and RoleHelper**
8. **Open draft PR** for Phase 1 for early feedback
9. **Continue through remaining phases** as outlined

---

## Questions or Concerns?

If you have questions or concerns about this refactoring plan, please:

1. Review the specific phase in question
2. Check the Risk Mitigation section for that concern
3. Consult the Success Metrics to understand goals
4. Comment on the tracking issue or contact the project maintainer

This plan is designed to be **iterative and safe** - each phase can be validated independently before proceeding to the next.

---

**Document Version:** 1.0  
**Created:** 2025-11-01  
**Last Updated:** 2025-11-01  
**Status:** AWAITING APPROVAL
