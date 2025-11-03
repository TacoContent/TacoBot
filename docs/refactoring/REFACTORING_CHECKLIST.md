# DiscordHelper Refactoring - Implementation Checklist

## Pre-Implementation

- [x] **Plan reviewed and approved** by project maintainer
- [x] **Timeline confirmed** (10 weeks acceptable)
- [x] **Team capacity verified** for 10-week effort
- [x] **Create tracking issue** in GitHub with all phases
- [x] **Set up project board** with phase columns

---

## Phase 1: Foundation & Infrastructure (Week 1)

### Setup

- [x] Create `bot/lib/helpers/` directory
- [x] Create `bot/lib/helpers/__init__.py` with placeholder exports
- [x] Create `tests/lib/helpers/` directory

### ContextHelper

- [x] Create `bot/lib/helpers/context_helper.py`
- [x] Implement `create_context()` method
- [x] Create `tests/lib/helpers/test_context_helper.py`
- [x] Write tests for:
  - [x] Standard parameter creation
  - [x] **kwargs merging
  - [x] None value handling
  - [x] Returned namedtuple has correct attributes
- [x] All ContextHelper tests passing ✅

### EntityHelper

- [x] Create `bot/lib/helpers/entity_helper.py`
- [x] Implement `get_or_fetch_user(userId)`
- [x] Implement `get_or_fetch_member(guildId, userId)`
- [x] Implement `get_or_fetch_role(guild, roleId)`
- [x] Implement `get_or_fetch_channel(channelId)`
- [x] Implement `get_by_name_or_id(iterable, nameOrId)`
- [x] Create `tests/lib/helpers/test_entity_helper.py`
- [x] Write tests for:
  - [x] Cache hit scenarios
  - [x] Cache miss + fetch scenarios
  - [x] NotFound error handling
  - [x] None/invalid ID handling
  - [x] Name vs ID lookup logic
- [x] All EntityHelper tests passing ✅

### RoleHelper

- [x] Create `bot/lib/helpers/role_helper.py`
- [x] Implement `add_remove_roles(user, check_list, add_list, remove_list, allow_everyone)`
- [x] Create `tests/lib/helpers/test_role_helper.py`
- [x] Write tests for:
  - [x] Role addition logic
  - [x] Role removal logic
  - [x] check_list filtering
  - [x] allow_everyone bypass
  - [x] Exception handling during operations
  - [x] Logging of role changes
- [x] All RoleHelper tests passing ✅

### Phase 1 Wrap-up

- [x] Update `bot/lib/helpers/__init__.py` to export all Phase 1 helpers
- [x] Run all Phase 1 tests ✅
- [x] Run linters (Black, isort) ✅
- [x] Run full test suite (no regressions) ✅
- [x] Create draft PR for Phase 1 for early feedback
- [x] Document Phase 1 helpers in `docs/lib/helpers/`

---

## Phase 2: Message & Taco Helpers (Week 2)

### MessageHelper

- [x] Create `bot/lib/helpers/message_helper.py`
- [x] Implement `move_message(message, targetChannel, ...)`
- [x] Implement `notify_bot_not_initialized(ctx, subcommand)`
- [x] Create `tests/lib/helpers/test_message_helper.py`
- [x] Write tests for:
  - [x] Embed extraction and merging
  - [x] Field removal logic
  - [x] Attachment handling
  - [x] Footer generation
  - [x] delete_original flag behavior
  - [x] Admin vs non-admin notification
- [x] All MessageHelper tests passing ✅

### TacoHelper

- [x] Create `bot/lib/helpers/taco_helper.py`
- [x] Implement `give_tacos(guildId, fromUser, toUser, reason, give_type, taco_amount)`
- [x] Implement `log_taco_transaction(guild_id, toMember, fromMember, count, total_tacos, reason, type)`
- [x] Implement `log_taco_purge(guild_id, toMember, fromMember, reason)`
- [x] Implement `get_taco_settings(guildId)`
- [x] Create `tests/lib/helpers/test_taco_helper.py`
- [x] Write tests for:
  - [x] Taco amount calculation from settings
  - [x] Database add_tacos call
  - [x] Database track_tacos_log call
  - [x] Log channel message formatting
  - [x] Plural/singular taco word logic
  - [x] Negative count handling (loss vs received)
  - [x] Purge logging
- [x] All TacoHelper tests passing ✅

### Phase 2 Wrap-up

- [x] Update `bot/lib/helpers/__init__.py` to export Phase 2 helpers
- [x] Run all Phase 2 tests ✅
- [x] Run linters (Black, isort) ✅
- [x] Run full test suite (no regressions) ✅
- [x] Update draft PR with Phase 2 changes
- [x] Document Phase 2 helpers in `docs/lib/helpers/`

---

## Phase 3: Prompt Helper (Week 3)

### PromptHelper

- [x] Create `bot/lib/helpers/prompt_helper.py`
- [x] Implement `ask_yes_no(ctx, targetChannel, question, ...)`
- [x] Implement `ask_channel(ctx, title, message, ...)`
- [x] Implement `ask_channel_by_name_or_id(ctx, title, description, timeout)`
- [x] Implement `ask_number(ctx, title, message, min_value, max_value, timeout)`
- [x] Implement `ask_text(ctx, targetChannel, title, message, timeout, color)`
- [x] Implement `ask_for_image_or_text(ctx, targetChannel, title, message, timeout, color)`
- [x] Implement `ask_role_list(ctx, title, message, ...)`
- [x] Create `tests/lib/helpers/test_prompt_helper.py`
- [x] Write tests for:
  - [x] Messaging.send_embed call
  - [x] bot.wait_for call with correct check function
  - [x] Timeout handling (asyncio.TimeoutError)
  - [x] Callback invocation
  - [x] User message cleanup (delete)
  - [x] DM vs guild channel behavior
  - [x] View integration (YesOrNoView, ChannelSelectView, RoleSelectView)
- [x] All PromptHelper tests passing ✅

### Phase 3 Wrap-up

- [x] Update `bot/lib/helpers/__init__.py` to export PromptHelper
- [x] Run all Phase 3 tests ✅
- [x] Run linters (Black, isort) ✅
- [x] Run full test suite (no regressions) ✅
- [x] Update draft PR with Phase 3 changes
- [x] Document PromptHelper in `docs/lib/helpers/prompt_helper.md`
- [x] All 6 helpers complete! 🎉

---

## Phase 4: Backward Compatibility Facade (Week 4)

### Facade Implementation

- [x] Modify `bot/lib/discordhelper.py` to create facade
- [x] Initialize all 6 helpers in `__init__`
- [x] Create delegation methods for all public methods:
  - [x] `create_context(...)` → `context_helper.create_context(...)`
  - [x] `get_or_fetch_user(userId)` → `entity_helper.get_or_fetch_user(userId)`
  - [x] `get_or_fetch_member(...)` → `entity_helper.get_or_fetch_member(...)`
  - [x] `get_or_fetch_role(...)` → `entity_helper.get_or_fetch_role(...)`
  - [x] `get_or_fetch_channel(...)` → `entity_helper.get_or_fetch_channel(...)`
  - [x] `get_by_name_or_id(...)` → `entity_helper.get_by_name_or_id(...)`
  - [x] `ask_yes_no(...)` → `prompt_helper.ask_yes_no(...)`
  - [x] `ask_channel(...)` → `prompt_helper.ask_channel(...)`
  - [x] `ask_channel_by_name_or_id(...)` → `prompt_helper.ask_channel_by_name_or_id(...)`
  - [x] `ask_number(...)` → `prompt_helper.ask_number(...)`
  - [x] `ask_text(...)` → `prompt_helper.ask_text(...)`
  - [x] `ask_for_image_or_text(...)` → `prompt_helper.ask_for_image_or_text(...)`
  - [x] `ask_role_list(...)` → `prompt_helper.ask_role_list(...)`
  - [x] `taco_give_user(...)` → `taco_helper.give_tacos(...)`
  - [x] `tacos_log(...)` → `taco_helper.log_taco_transaction(...)`
  - [x] `taco_purge_log(...)` → `taco_helper.log_taco_purge(...)`
  - [x] `_get_tacos_settings(...)` → `taco_helper.get_taco_settings(...)`
  - [x] `move_message(...)` → `message_helper.move_message(...)`
  - [x] `notify_bot_not_initialized(...)` → `message_helper.notify_bot_not_initialized(...)`
  - [x] `add_remove_roles(...)` → `role_helper.add_remove_roles(...)`
- [x] Expose legacy properties:
  - [x] `self.settings` → `self.taco_helper.settings`
  - [x] `self.log` → `self.entity_helper.log`
  - [x] `self.messaging` → `self.message_helper.messaging`
  - [x] `self.tacos_db` → `self.taco_helper.tacos_db`
- [x] Add deprecation warnings to class docstring

### Integration Testing

- [x] Create `tests/lib/test_discordhelper_facade.py`
- [x] Test all delegation methods work correctly
- [x] Test all legacy properties are accessible
- [x] Run existing DiscordHelper tests against facade
- [x] All integration tests passing ✅

### Documentation

- [x] Create `docs/refactoring/discordhelper_migration_guide.md`
- [x] Document before/after examples for each helper type
- [x] Add common migration patterns
- [x] Add FAQ section
- [x] Update deprecation notices in DiscordHelper docstrings

### Phase 4 Wrap-up

- [x] Run all tests (unit + integration) ✅
- [x] Run linters (Black, isort) ✅
- [x] Run full test suite (no regressions) ✅
- [x] Verify all existing code still works ✅
- [x] Update draft PR with Phase 4 changes
- [x] Mark PR as "Ready for early review" (optional)

---

## Phase 5: Incremental Migration - Cogs (Weeks 5-7)

### Week 5: Low Complexity Cogs (10-12 cogs)

- [x] **guild_track.py** (EntityHelper only)
- [x] **message_track.py** (EntityHelper only)
- [x] **voicechat.py** (EntityHelper only)
- [x] **command_sync.py** (EntityHelper only)
- [x] **free_games.py** (EntityHelper, MessageHelper)
- [x] **giphy.py** (EntityHelper, PromptHelper)
- [ ] **photo_post.py** (EntityHelper, PromptHelper)
- [ ] **twitter_preview.py** (EntityHelper)
- [ ] **message_preview.py** (EntityHelper)
- [ ] **_amazon_links.py** (EntityHelper)
- [ ] Run tests for each migrated cog ✅
- [ ] Week 5 complete ✅

### Week 6: Medium Complexity Cogs (10-12 cogs)

- [ ] **join_leave.py** (EntityHelper, MessageHelper, TacoHelper)
- [x] **birthday.py** (EntityHelper, PromptHelper, TacoHelper)
- [ ] **introduction.py** (EntityHelper, PromptHelper)
- [ ] **invite_tracker.py** (EntityHelper, TacoHelper)
- [ ] **restricted.py** (EntityHelper, RoleHelper)
- [ ] **server_event.py** (EntityHelper, PromptHelper)
- [ ] **streamteam.py** (EntityHelper, PromptHelper, RoleHelper)
- [ ] **wdyctw.py** (EntityHelper, PromptHelper)
- [ ] **account_link.py** (EntityHelper, PromptHelper)
- [x] **game_keys.py** (EntityHelper, PromptHelper)
- [ ] **_lfg.py** (EntityHelper, PromptHelper)
- [ ] Run tests for each migrated cog ✅
- [ ] Week 6 complete ✅

### Week 7: High Complexity Cogs (remaining cogs)

- [ ] **tacos.py** (All helpers)
- [ ] **announcements.py** (EntityHelper, PromptHelper, MessageHelper)
- [ ] **suggestions.py** (EntityHelper, PromptHelper, MessageHelper)
- [ ] **move_message.py** (EntityHelper, MessageHelper)
- [ ] **minecraft.py** (EntityHelper, PromptHelper, TacoHelper)
- [ ] **new_account_check.py** (EntityHelper, RoleHelper, MessageHelper)
- [ ] **live_now.py** (EntityHelper, PromptHelper, TacoHelper)
- [ ] **taco_tuesday.py** (EntityHelper, PromptHelper, TacoHelper)
- [ ] **tech_thursday.py** (EntityHelper, PromptHelper, TacoHelper)
- [ ] **mental_monday.py** (EntityHelper, PromptHelper, TacoHelper)
- [ ] **tqotd.py** (EntityHelper, PromptHelper, TacoHelper)
- [ ] **trivia.py** (EntityHelper, PromptHelper, TacoHelper)
- [ ] **twitchinfo.py** (EntityHelper, PromptHelper)
- [ ] **user_lookup.py** (EntityHelper, PromptHelper)
- [ ] **tacopost.py** (EntityHelper, TacoHelper)
- [ ] **help.py** (EntityHelper, PromptHelper)
- [ ] **_leave_survey.py** (EntityHelper, PromptHelper)
- [ ] Run tests for each migrated cog ✅
- [ ] Week 7 complete ✅

### Phase 5 Wrap-up

- [ ] All cogs migrated ✅
- [ ] Run full cog test suite ✅
- [ ] Run linters (Black, isort) ✅
- [ ] No functionality regressions ✅
- [ ] Update PR with all cog migrations

---

## Phase 6: HTTP Handler Migration (Week 8)

### Base Handlers

- [ ] **BaseHttpHandler.py**
- [ ] **ApiHttpHandler.py**
- [ ] **BaseWebhookHandler.py**

### API v1 Handlers

- [ ] **GuildRolesApiHandler.py**
- [ ] **GuildMessagesApiHandler.py**
- [ ] **GuildLookupApiHandler.py**
- [ ] **GuildEmojisApiHandler.py**
- [ ] **GuildChannelsApiHandler.py**
- [ ] **HealthcheckApiHandler.py**
- [ ] **MinecraftApiHandler.py**
- [ ] **JoinWhitelistApiHandler.py**
- [ ] **SettingsApiHandler.py**
- [ ] **SwaggerHttpHandler.py**
- [ ] **TacoPermissionsApiHandler.py**

### Webhook Handlers

- [ ] **MinecraftPlayerWebhookHandler.py**
- [ ] **ShiftCodeWebhookHandler.py**
- [ ] **GuildResolver.py** (helper for webhooks)

### HTTP Handler Cog

- [ ] **httphandler.py** (cog)

### Phase 6 Wrap-up

- [ ] All HTTP handlers migrated ✅
- [ ] Run API tests ✅
- [ ] Run swagger sync check (`python scripts/swagger_sync.py --check`) ✅
- [ ] All endpoints functional ✅
- [ ] Run linters (Black, isort) ✅
- [ ] Update PR with handler migrations

---

## Phase 7: Migration of Permissions & Utilities (Week 9)

### Library Utilities

- [ ] **bot/lib/permissions.py** (migrate to EntityHelper)
- [ ] Search `bot/lib/` for other DiscordHelper usages
- [ ] Migrate any additional files found

### Full Integration Testing

- [ ] Run all unit tests ✅
- [ ] Run all integration tests ✅
- [ ] Run all API tests ✅
- [ ] Run all cog tests ✅
- [ ] Run full test suite with coverage ✅
- [ ] Verify 80%+ coverage maintained ✅

### Phase 7 Wrap-up

- [ ] All non-facade code using new helpers ✅
- [ ] Run linters (Black, isort) ✅
- [ ] CI pipeline green ✅
- [ ] Update PR with lib migrations

---

## Phase 8: Cleanup & Deprecation (Week 10)

### Deprecation Warnings

- [ ] Add deprecation warnings to DiscordHelper facade class
- [ ] Update DiscordHelper docstring with deprecation notice
- [ ] Add links to new helpers in deprecation message

### Documentation Phase 8

- [ ] **README.md**: Add note about new helper structure
- [ ] **docs/lib/helpers/README.md**: Overview of all helpers
- [ ] **docs/lib/helpers/entity_helper.md**: EntityHelper docs
- [ ] **docs/lib/helpers/prompt_helper.md**: PromptHelper docs
- [ ] **docs/lib/helpers/taco_helper.md**: TacoHelper docs
- [ ] **docs/lib/helpers/message_helper.md**: MessageHelper docs
- [ ] **docs/lib/helpers/role_helper.md**: RoleHelper docs
- [ ] **docs/lib/helpers/context_helper.md**: ContextHelper docs
- [ ] **CHANGELOG.md**: Document refactoring changes
- [ ] **.github/copilot-instructions.md**: Update with new patterns
- [ ] Migration guide complete with all examples

### Deprecation Timeline

- [ ] Create deprecation timeline (6-12 months for facade removal)
- [ ] Add timeline to CHANGELOG.md
- [ ] Add timeline to project roadmap

### Final Quality Checks

- [ ] Run full test suite with coverage ✅
- [ ] Ensure 80%+ coverage maintained ✅
- [ ] Run Black formatter ✅
- [ ] Run isort ✅
- [ ] Run swagger sync check ✅
- [ ] All linters passing ✅
- [ ] CI pipeline green ✅

### Pull Request

- [ ] Update PR description with:
  - [ ] Link to this refactoring plan
  - [ ] Summary of changes
  - [ ] Test coverage improvements
  - [ ] Note: No breaking changes
  - [ ] Migration guide link
- [ ] Mark PR as "Ready for review"
- [ ] Request review from maintainer
- [ ] Address review comments
- [ ] PR approved ✅
- [ ] Merge to develop branch ✅

---

## Phase 9: Future Removal (Optional - 6-12 months later)

### Facade Removal

- [ ] **Confirm** all code migrated off facade
- [ ] **Search** for any remaining DiscordHelper imports
- [ ] **Delete** `bot/lib/discordhelper.py`
- [ ] **Remove** facade tests
- [ ] **Update** any remaining references

### Documentation Cleanup

- [ ] Remove all DiscordHelper references from docs
- [ ] Update examples to use new helpers exclusively
- [ ] Update migration guide to "historical" status

### Final Checks

- [ ] Run full test suite ✅
- [ ] No references to DiscordHelper remain ✅
- [ ] CI pipeline green ✅
- [ ] Create PR for facade removal
- [ ] PR approved and merged ✅

---

## Progress Tracking

### Overall Progress

- [x] Phase 1: Foundation (Week 1)
- [x] Phase 2: Message & Taco (Week 2)
- [x] Phase 3: Prompt Helper (Week 3)
- [ ] Phase 4: Facade (Week 4)
- [ ] Phase 5: Cog Migration (Weeks 5-7)
- [ ] Phase 6: HTTP Migration (Week 8)
- [ ] Phase 7: Lib Migration (Week 9)
- [ ] Phase 8: Cleanup (Week 10)
- [ ] Phase 9: Removal (Optional, future)

### Key Metrics

- **Test Coverage**: ___% (Target: 80%+)
- **Cogs Migrated**: ___/30+ (Target: 100%)
- **Handlers Migrated**: ___/15+ (Target: 100%)
- **Lib Files Migrated**: ___/2+ (Target: 100%)
- **DiscordHelper Usage**: ___ files (Target: 0, excluding facade)

---

## Notes

Use this section to track blockers, decisions, or important notes:

- **Date**: Decision/note
- **Date**: Decision/note

---

**Status**: NOT STARTED  
**Started**: ___________  
**Completed**: ___________  
**Last Updated**: 2025-11-02
