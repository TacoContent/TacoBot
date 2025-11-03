# DiscordHelper Migration Guide

This guide helps you migrate from the monolithic `DiscordHelper` to the new specialized helper classes.

## Table of Contents

- [Overview](#overview)
- [Why Migrate?](#why-migrate)
- [New Helper Classes](#new-helper-classes)
- [Migration Patterns](#migration-patterns)
  - [EntityHelper](#entityhelper)
  - [MessageHelper](#messagehelper)
  - [PromptHelper](#prompthelper)
  - [RoleHelper](#rolehelper)
  - [TacoHelper](#tacohelper)
  - [ContextHelper](#contexthelper)
- [Common Migration Scenarios](#common-migration-scenarios)
- [FAQ](#faq)
- [Deprecation Timeline](#deprecation-timeline)

---

## Overview

The `DiscordHelper` class has been refactored into six specialized helper classes, each focused on a specific domain:

1. **EntityHelper** - Discord entity fetching (users, members, roles, channels)
2. **MessageHelper** - Message operations and notifications
3. **PromptHelper** - User interaction prompts
4. **RoleHelper** - Bulk role operations
5. **TacoHelper** - Taco system operations
6. **ContextHelper** - Context object creation

**Backward Compatibility:** The original `DiscordHelper` remains as a facade that delegates to these new helpers, so existing code continues to work without changes.

---

## Why Migrate?

### Benefits of the New Architecture

✅ **Single Responsibility** - Each helper focuses on one domain  
✅ **Easier Testing** - Smaller, focused classes are easier to test  
✅ **Better Reusability** - Use only the helpers you need  
✅ **Reduced Dependencies** - TacoHelper doesn't need prompt logic  
✅ **Improved Maintainability** - Changes are isolated to relevant helpers  
✅ **Clearer Code** - Intent is clearer when using specialized helpers

### Migration Approach

You have two options:

1. **Keep using DiscordHelper** (no changes needed, but deprecated)
2. **Migrate to new helpers** (recommended for new code and future-proofing)

---

## New Helper Classes

### Import Paths

```python
# Old (still works via facade)
from bot.lib.discordhelper import DiscordHelper

# New (recommended)
from bot.lib.helpers import (
    EntityHelper,
    MessageHelper,
    PromptHelper,
    RoleHelper,
    TacoHelper,
    ContextHelper,
)
```

### Helper Initialization

```python
# All helpers require a bot instance
class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize the helpers you need
        self.entity_helper = EntityHelper(bot)
        self.message_helper = MessageHelper(bot)
        self.prompt_helper = PromptHelper(bot)
        self.role_helper = RoleHelper(bot)
        self.taco_helper = TacoHelper(bot)  # Also needs entity_helper
        self.context_helper = ContextHelper(bot)
```

**Note:** `TacoHelper` requires an `EntityHelper` instance:

```python
# TacoHelper initialization
self.entity_helper = EntityHelper(bot)
self.taco_helper = TacoHelper(bot, self.entity_helper)
```

---

## Migration Patterns

### EntityHelper

**Purpose:** Fetch Discord entities (users, members, roles, channels) with cache-first logic.

#### Before (DiscordHelper)

```python
from bot.lib.discordhelper import DiscordHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.discord_helper = DiscordHelper(bot)
    
    async def get_user_info(self, user_id: int):
        user = await self.discord_helper.get_or_fetch_user(user_id)
        return user
    
    async def get_member(self, guild_id: int, user_id: int):
        member = await self.discord_helper.get_or_fetch_member(guild_id, user_id)
        return member
    
    async def get_channel(self, channel_id: int):
        channel = await self.discord_helper.get_or_fetch_channel(channel_id)
        return channel
    
    def find_role(self, guild, role_name_or_id):
        role = self.discord_helper.get_by_name_or_id(guild.roles, role_name_or_id)
        return role
```

#### After (EntityHelper)

```python
from bot.lib.helpers import EntityHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.entity_helper = EntityHelper(bot)
    
    async def get_user_info(self, user_id: int):
        user = await self.entity_helper.get_or_fetch_user(user_id)
        return user
    
    async def get_member(self, guild_id: int, user_id: int):
        member = await self.entity_helper.get_or_fetch_member(guild_id, user_id)
        return member
    
    async def get_channel(self, channel_id: int):
        channel = await self.entity_helper.get_or_fetch_channel(channel_id)
        return channel
    
    def find_role(self, guild, role_name_or_id):
        role = self.entity_helper.get_by_name_or_id(guild.roles, role_name_or_id)
        return role
```

**Methods:**

- `get_or_fetch_user(user_id)` - Get user from cache or fetch from API
- `get_or_fetch_member(guild_id, user_id)` - Get member from cache or fetch
- `get_or_fetch_role(guild, role_id)` - Get role from cache or fetch
- `get_or_fetch_channel(channel_id)` - Get channel from cache or fetch
- `get_by_name_or_id(iterable, name_or_id)` - Find item by name or ID

---

### MessageHelper

**Purpose:** Move messages and send bot initialization notifications.

#### Before (DiscordHelper) MessageHelper

```python
from bot.lib.discordhelper import DiscordHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.discord_helper = DiscordHelper(bot)
    
    @commands.command()
    async def move(self, ctx, message_id: int, channel: discord.TextChannel):
        """Move a message to another channel."""
        message = await ctx.channel.fetch_message(message_id)
        await self.discord_helper.move_message(
            message, 
            channel, 
            reason="Moved by moderator",
            delete_original=True
        )
    
    @commands.command()
    async def restricted_command(self, ctx):
        """A command that requires setup."""
        if not self.is_initialized():
            await self.discord_helper.notify_bot_not_initialized(ctx, "restricted_command")
            return
        # ... command logic
```

#### After (MessageHelper)

```python
from bot.lib.helpers import MessageHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_helper = MessageHelper(bot)
    
    @commands.command()
    async def move(self, ctx, message_id: int, channel: discord.TextChannel):
        """Move a message to another channel."""
        message = await ctx.channel.fetch_message(message_id)
        await self.message_helper.move_message(
            message, 
            channel, 
            reason="Moved by moderator",
            delete_original=True
        )
    
    @commands.command()
    async def restricted_command(self, ctx):
        """A command that requires setup."""
        if not self.is_initialized():
            await self.message_helper.notify_bot_not_initialized(ctx, "restricted_command")
            return
        # ... command logic
```

**Methods:**

- `move_message(message, target_channel, reason, delete_original)` - Move message with embeds/attachments
- `notify_bot_not_initialized(ctx, subcommand)` - Send setup required notification

---

### PromptHelper

**Purpose:** Interactive prompts for user input (yes/no, text, numbers, channel/role selection).

#### Before (DiscordHelper) PromptHelper

```python
from bot.lib.discordhelper import DiscordHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.discord_helper = DiscordHelper(bot)
    
    @commands.command()
    async def setup(self, ctx):
        """Interactive setup command."""
        # Ask yes/no question
        confirmed = await self.discord_helper.ask_yes_no(
            ctx, ctx.channel, 
            question="Do you want to enable this feature?",
            title="Setup Confirmation"
        )
        if not confirmed:
            return
        
        # Ask for text input
        description = await self.discord_helper.ask_text(
            ctx, ctx.channel,
            title="Feature Description",
            message="Enter a description for this feature:"
        )
        
        # Ask for number input
        limit = await self.discord_helper.ask_number(
            ctx,
            title="Set Limit",
            message="Enter maximum limit (1-100):",
            min_value=1,
            max_value=100
        )
        
        # Ask for channel selection
        channel = await self.discord_helper.ask_channel(
            ctx,
            title="Select Channel",
            message="Which channel should be used?"
        )
        
        # Ask for role selection
        roles = await self.discord_helper.ask_role_list(
            ctx,
            title="Select Roles",
            message="Choose roles to grant access:"
        )
```

#### After (PromptHelper)

```python
from bot.lib.helpers import PromptHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prompt_helper = PromptHelper(bot)
    
    @commands.command()
    async def setup(self, ctx):
        """Interactive setup command."""
        # Ask yes/no question
        confirmed = await self.prompt_helper.ask_yes_no(
            ctx, ctx.channel, 
            question="Do you want to enable this feature?",
            title="Setup Confirmation"
        )
        if not confirmed:
            return
        
        # Ask for text input
        description = await self.prompt_helper.ask_text(
            ctx, ctx.channel,
            title="Feature Description",
            message="Enter a description for this feature:"
        )
        
        # Ask for number input
        limit = await self.prompt_helper.ask_number(
            ctx,
            title="Set Limit",
            message="Enter maximum limit (1-100):",
            min_value=1,
            max_value=100
        )
        
        # Ask for channel selection
        channel = await self.prompt_helper.ask_channel(
            ctx,
            title="Select Channel",
            message="Which channel should be used?"
        )
        
        # Ask for role selection
        roles = await self.prompt_helper.ask_role_list(
            ctx,
            title="Select Roles",
            message="Choose roles to grant access:"
        )
```

**Methods:**

- `ask_yes_no(ctx, channel, question, title, timeout)` - Yes/No confirmation
- `ask_text(ctx, channel, title, message, timeout, color)` - Text input
- `ask_number(ctx, title, message, min_value, max_value, timeout)` - Number input
- `ask_channel(ctx, title, message, timeout)` - Channel selection dropdown
- `ask_channel_by_name_or_id(ctx, title, description, timeout)` - Channel by text input
- `ask_role_list(ctx, title, message, timeout, max_values)` - Role selection dropdown
- `ask_for_image_or_text(ctx, channel, title, message, timeout, color)` - Image or text input

---

### RoleHelper

**Purpose:** Bulk add/remove roles with filtering and validation.

#### Before (DiscordHelper) RoleHelper

```python
from bot.lib.discordhelper import DiscordHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.discord_helper = DiscordHelper(bot)
    
    @commands.command()
    async def update_roles(self, ctx, member: discord.Member):
        """Update member roles based on criteria."""
        await self.discord_helper.add_remove_roles(
            user=member,
            check_list=["123456789"],  # Only modify if has this role
            add_list=["987654321"],     # Add these role IDs
            remove_list=["555555555"],  # Remove these role IDs
            allow_everyone=False        # Don't allow @everyone role
        )
```

#### After (RoleHelper)

```python
from bot.lib.helpers import RoleHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_helper = RoleHelper(bot)
    
    @commands.command()
    async def update_roles(self, ctx, member: discord.Member):
        """Update member roles based on criteria."""
        await self.role_helper.add_remove_roles(
            user=member,
            check_list=["123456789"],  # Only modify if has this role
            add_list=["987654321"],     # Add these role IDs
            remove_list=["555555555"],  # Remove these role IDs
            allow_everyone=False        # Don't allow @everyone role
        )
```

**Methods:**

- `add_remove_roles(user, check_list, add_list, remove_list, allow_everyone)` - Bulk role operations

---

### TacoHelper

**Purpose:** Taco system operations (giving, logging, settings).

#### Before (DiscordHelper) TacoHelper

```python
from bot.lib.discordhelper import DiscordHelper
from bot.lib.enums.tacotypes import TacoTypes

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.discord_helper = DiscordHelper(bot)
    
    @commands.command()
    async def give_taco(self, ctx, member: discord.Member, *, reason: str):
        """Give a taco to someone."""
        count = await self.discord_helper.taco_give_user(
            guildId=ctx.guild.id,
            fromUser=ctx.author,
            toUser=member,
            reason=reason,
            give_type=TacoTypes.CUSTOM,
            taco_amount=1
        )
        await ctx.send(f"Gave taco! {member.mention} now has {count} tacos!")
    
    async def log_taco_transaction(self, guild_id, to_member, from_member, count, total):
        """Log a taco transaction."""
        await self.discord_helper.tacos_log(
            guild_id=guild_id,
            toMember=to_member,
            fromMember=from_member,
            count=count,
            total_tacos=total,
            reason="Daily reward",
            type=TacoTypes.REACTION
        )
    
    def get_settings(self, guild_id):
        """Get taco settings for guild."""
        return self.discord_helper._get_tacos_settings(guild_id)
```

#### After (TacoHelper)

```python
from bot.lib.helpers import EntityHelper, TacoHelper
from bot.lib.enums.tacotypes import TacoTypes

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.entity_helper = EntityHelper(bot)
        self.taco_helper = TacoHelper(bot, self.entity_helper)
    
    @commands.command()
    async def give_taco(self, ctx, member: discord.Member, *, reason: str):
        """Give a taco to someone."""
        count = await self.taco_helper.give_tacos(
            guildId=ctx.guild.id,
            fromUser=ctx.author,
            toUser=member,
            reason=reason,
            give_type=TacoTypes.CUSTOM,
            taco_amount=1
        )
        await ctx.send(f"Gave taco! {member.mention} now has {count} tacos!")
    
    async def log_taco_transaction(self, guild_id, to_member, from_member, count, total):
        """Log a taco transaction."""
        await self.taco_helper.log_taco_transaction(
            guild_id=guild_id,
            toMember=to_member,
            fromMember=from_member,
            count=count,
            total_tacos=total,
            reason="Daily reward",
            type=TacoTypes.REACTION
        )
    
    def get_settings(self, guild_id):
        """Get taco settings for guild."""
        return self.taco_helper.get_taco_settings(guild_id)
```

**Methods:**

- `give_tacos(guildId, fromUser, toUser, reason, give_type, taco_amount)` - Give tacos to user
- `log_taco_transaction(guild_id, toMember, fromMember, count, total_tacos, reason, type)` - Log transaction
- `log_taco_purge(guild_id, toMember, fromMember, reason)` - Log purge event
- `get_taco_settings(guildId)` - Get taco settings for guild

---

### ContextHelper

**Purpose:** Create mock context objects for testing.

#### Before (DiscordHelper) ContextHelper

```python
from bot.lib.discordhelper import DiscordHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.discord_helper = DiscordHelper(bot)
    
    def create_test_context(self):
        """Create a test context."""
        ctx = self.discord_helper.create_context(
            bot=self.bot,
            author="test_author",
            guild_id=123456789,
            channel=None
        )
        return ctx
```

#### After (ContextHelper)

```python
from bot.lib.helpers import ContextHelper

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.context_helper = ContextHelper(bot)
    
    def create_test_context(self):
        """Create a test context."""
        ctx = self.context_helper.create_context(
            bot=self.bot,
            author="test_author",
            guild_id=123456789,
            channel=None
        )
        return ctx
```

**Methods:**

- `create_context(**kwargs)` - Create namedtuple context with arbitrary attributes

---

## Common Migration Scenarios

### Scenario 1: Cog Using Multiple Helpers

**Before:**

```python
from bot.lib.discordhelper import DiscordHelper

class FeatureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.discord_helper = DiscordHelper(bot)
    
    @commands.command()
    async def feature(self, ctx):
        # Fetch entities
        user = await self.discord_helper.get_or_fetch_user(123)
        
        # Prompt user
        confirmed = await self.discord_helper.ask_yes_no(ctx, ctx.channel, "Continue?")
        
        # Give tacos
        await self.discord_helper.taco_give_user(
            ctx.guild.id, ctx.author, user, "feature", TacoTypes.CUSTOM, 1
        )
```

**After:**

```python
from bot.lib.helpers import EntityHelper, PromptHelper, TacoHelper

class FeatureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize only the helpers you need
        self.entity_helper = EntityHelper(bot)
        self.prompt_helper = PromptHelper(bot)
        self.taco_helper = TacoHelper(bot, self.entity_helper)
    
    @commands.command()
    async def feature(self, ctx):
        # Fetch entities
        user = await self.entity_helper.get_or_fetch_user(123)
        
        # Prompt user
        confirmed = await self.prompt_helper.ask_yes_no(ctx, ctx.channel, "Continue?")
        
        # Give tacos
        await self.taco_helper.give_tacos(
            ctx.guild.id, ctx.author, user, "feature", TacoTypes.CUSTOM, 1
        )
```

### Scenario 2: HTTP Handler Migration

**Before:**

```python
from bot.lib.discordhelper import DiscordHelper
from bot.lib.http.handlers.api.base import ApiHttpHandler

class GuildApiHandler(ApiHttpHandler):
    def __init__(self, bot):
        super().__init__(bot)
        self.discord_helper = DiscordHelper(bot)
    
    async def get_guild_member(self, request, uri_variables):
        guild_id = int(uri_variables['guild_id'])
        user_id = int(uri_variables['user_id'])
        
        member = await self.discord_helper.get_or_fetch_member(guild_id, user_id)
        if not member:
            raise HttpResponseException(404, {}, json.dumps({"error": "Member not found"}))
        
        return HttpResponse(200, {}, json.dumps({"id": member.id, "name": member.name}))
```

**After:**

```python
from bot.lib.helpers import EntityHelper
from bot.lib.http.handlers.api.base import ApiHttpHandler

class GuildApiHandler(ApiHttpHandler):
    def __init__(self, bot):
        super().__init__(bot)
        self.entity_helper = EntityHelper(bot)
    
    async def get_guild_member(self, request, uri_variables):
        guild_id = int(uri_variables['guild_id'])
        user_id = int(uri_variables['user_id'])
        
        member = await self.entity_helper.get_or_fetch_member(guild_id, user_id)
        if not member:
            raise HttpResponseException(404, {}, json.dumps({"error": "Member not found"}))
        
        return HttpResponse(200, {}, json.dumps({"id": member.id, "name": member.name}))
```

### Scenario 3: Accessing Properties

**Before:**

```python
class MyCog(commands.Cog):
    def __init__(self, bot):
        self.discord_helper = DiscordHelper(bot)
    
    def get_settings(self):
        return self.discord_helper.settings
    
    def get_logger(self):
        return self.discord_helper.log
    
    def get_messaging(self):
        return self.discord_helper.messaging
```

**After:**

```python
class MyCog(commands.Cog):
    def __init__(self, bot):
        self.entity_helper = EntityHelper(bot)
        self.message_helper = MessageHelper(bot)
        self.taco_helper = TacoHelper(bot, self.entity_helper)
    
    def get_settings(self):
        # Settings available on multiple helpers
        return self.entity_helper.settings
    
    def get_logger(self):
        # Logger available on all helpers
        return self.entity_helper.log
    
    def get_messaging(self):
        # Messaging only on MessageHelper
        return self.message_helper.messaging
    
    def get_tacos_db(self):
        # Tacos DB only on TacoHelper
        return self.taco_helper.tacos_db
```

---

## FAQ

### Q: Do I need to migrate my code immediately?

**A:** No. The `DiscordHelper` facade maintains full backward compatibility. Your existing code will continue to work without any changes. However, we recommend migrating new code to use the specialized helpers.

### Q: What happens if I keep using DiscordHelper?

**A:** It will continue to work through the facade pattern. However, you'll see deprecation warnings in logs, and the facade will eventually be removed in a future major version (6-12 months from now).

### Q: Can I mix old and new approaches?

**A:** Yes! You can gradually migrate. Some cogs can use `DiscordHelper` while others use the new helpers. The facade ensures they all work together.

### Q: Which helper should I use for X?

Use this decision tree:

- **Fetching users/members/channels/roles?** → `EntityHelper`
- **Moving messages or showing "not initialized" messages?** → `MessageHelper`
- **Asking users for input (yes/no, text, numbers, selections)?** → `PromptHelper`
- **Bulk adding/removing roles?** → `RoleHelper`
- **Taco operations (give, log, settings)?** → `TacoHelper`
- **Creating test contexts?** → `ContextHelper`

### Q: Why does TacoHelper need EntityHelper?

**A:** `TacoHelper` uses `EntityHelper.get_or_fetch_channel()` to fetch the taco log channel when logging transactions. This dependency injection makes the code more testable and modular.

### Q: How do I access settings/log/messaging/tacos_db?

**Property Locations:**

```python
# Settings - available on most helpers
entity_helper.settings
message_helper.settings
prompt_helper.settings
role_helper.settings
taco_helper.settings

# Log - available on all helpers
entity_helper.log
message_helper.log
prompt_helper.log
role_helper.log
taco_helper.log
context_helper.log

# Messaging - only on MessageHelper
message_helper.messaging

# Tacos DB - only on TacoHelper
taco_helper.tacos_db
```

### Q: How do I test code that uses helpers?

**A:** Mock the specific helpers you need:

```python
from unittest.mock import AsyncMock, MagicMock
import pytest

class TestMyCog:
    @pytest.fixture
    def mock_entity_helper(self):
        helper = MagicMock()
        helper.get_or_fetch_user = AsyncMock(return_value=MagicMock(id=123))
        return helper
    
    def test_my_command(self, mock_entity_helper):
        cog = MyCog(bot=MagicMock())
        cog.entity_helper = mock_entity_helper
        
        # Test your cog
        # ...
```

### Q: What if I find a bug in a helper?

**A:** Report it in GitHub issues with the `refactoring` label. Include:

- Which helper has the issue
- Expected vs actual behavior
- Minimal reproduction code

---

## Deprecation Timeline

### Current Status (Phase 4 - November 2025)

✅ All helpers implemented and tested  
✅ Facade in place for backward compatibility  
✅ Migration guide published  
🔄 Deprecation warnings added to DiscordHelper  

### Phase 5-7 (Weeks 5-9)

- Migrate all cogs, HTTP handlers, and lib utilities to new helpers
- No breaking changes; facade remains functional

### Phase 8 (Week 10)

- Add formal deprecation notices to documentation
- Update all examples to use new helpers
- Set removal date for facade (6-12 months)

### Phase 9 (6-12 months after Phase 8)

- Remove DiscordHelper facade
- All code must use new helpers directly
- Breaking change; requires major version bump

---

## Need Help?

- **Documentation:** See individual helper docs in `docs/lib/helpers/`
- **Examples:** Check migrated cogs in `bot/cogs/` (after Phase 5)
- **Issues:** Create a GitHub issue with the `refactoring` label
- **Questions:** Ask in the project Discord or discussion forum

---

**Last Updated:** November 2, 2025  
**Refactoring Phase:** 4 (Facade Implementation)  
**Status:** Active Migration Period
