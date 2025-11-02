# DiscordHelper Refactoring - Quick Reference

## Overview

Breaking down the **800+ line DiscordHelper class** into **6 focused helper classes**.

---

## The New Helpers

### 1️⃣ **EntityHelper** - Discord Entity Fetching

**Location:** `bot/lib/helpers/entity_helper.py`

**Purpose:** Fetch users, members, roles, channels from Discord API

**Methods:**

- `get_or_fetch_user(userId)` - Get Discord user by ID
- `get_or_fetch_member(guildId, userId)` - Get guild member
- `get_or_fetch_role(guild, roleId)` - Get role from guild
- `get_or_fetch_channel(channelId)` - Get channel by ID
- `get_by_name_or_id(iterable, nameOrId)` - Generic lookup

**Usage:**

```python
from bot.lib.helpers import EntityHelper

entity_helper = EntityHelper(bot)
user = await entity_helper.get_or_fetch_user(123456)
```

---

### 2️⃣ **PromptHelper** - User Interactions

**Location:** `bot/lib/helpers/prompt_helper.py`

**Purpose:** All user input prompts (yes/no, text, numbers, selections)

**Methods:**

- `ask_yes_no(...)` - Yes/No confirmation
- `ask_channel(...)` - Channel selection
- `ask_number(...)` - Numeric input
- `ask_text(...)` - Text input
- `ask_for_image_or_text(...)` - Image or text input
- `ask_role_list(...)` - Role selection

**Usage:**

```python
from bot.lib.helpers import PromptHelper

prompt_helper = PromptHelper(bot)
response = await prompt_helper.ask_text(ctx, ctx.channel, "Enter your name:")
```

---

### 3️⃣ **TacoHelper** - Taco System

**Location:** `bot/lib/helpers/taco_helper.py`

**Purpose:** Taco giving, logging, tracking

**Methods:**

- `give_tacos(guildId, fromUser, toUser, reason, give_type, taco_amount)`
- `log_taco_transaction(guild_id, toMember, fromMember, count, total_tacos, reason, type)`
- `log_taco_purge(guild_id, toMember, fromMember, reason)`
- `get_taco_settings(guildId)`

**Usage:**

```python
from bot.lib.helpers import TacoHelper

taco_helper = TacoHelper(bot)
total = await taco_helper.give_tacos(guild_id, from_user, to_user, "Great help!", tacotypes.TacoTypes.CUSTOM, 5)
```

---

### 4️⃣ **MessageHelper** - Message Operations

**Location:** `bot/lib/helpers/message_helper.py`

**Purpose:** Message moving, bot notifications

**Methods:**

- `move_message(message, targetChannel, author, who, reason, ...)`
- `notify_bot_not_initialized(ctx, subcommand)`

**Usage:**

```python
from bot.lib.helpers import MessageHelper

message_helper = MessageHelper(bot)
await message_helper.move_message(message, target_channel, delete_original=True)
```

---

### 5️⃣ **RoleHelper** - Role Management

**Location:** `bot/lib/helpers/role_helper.py`

**Purpose:** Bulk role add/remove operations

**Methods:**

- `add_remove_roles(user, check_list, add_list, remove_list, allow_everyone)`

**Usage:**

```python
from bot.lib.helpers import RoleHelper

role_helper = RoleHelper(bot)
await role_helper.add_remove_roles(member, check_roles, add_roles, remove_roles)
```

---

### 6️⃣ **ContextHelper** - Testing Utilities

**Location:** `bot/lib/helpers/context_helper.py`

**Purpose:** Create mock context objects for testing

**Methods:**

- `create_context(bot, author, guild, channel, message, ...)`

**Usage:**

```python
from bot.lib.helpers import ContextHelper

context_helper = ContextHelper()
ctx = context_helper.create_context(bot=bot, author=user, guild=guild, channel=channel)
```

---

## Migration Example

### Before (Old Way)

```python
from bot.lib import discordhelper

class MyCog:
    def __init__(self, bot):
        self.bot = bot
        self.discord_helper = discordhelper.DiscordHelper(bot)
    
    async def my_command(self, ctx):
        user = await self.discord_helper.get_or_fetch_user(123)
        await self.discord_helper.taco_give_user(ctx.guild.id, ctx.author, user, "Good job!", tacotypes.TacoTypes.CUSTOM, 5)
        response = await self.discord_helper.ask_text(ctx, ctx.channel, "What's your favorite color?")
```

### After (New Way)

```python
from bot.lib.helpers import EntityHelper, TacoHelper, PromptHelper

class MyCog:
    def __init__(self, bot):
        self.bot = bot
        self.entity_helper = EntityHelper(bot)
        self.taco_helper = TacoHelper(bot)
        self.prompt_helper = PromptHelper(bot)
    
    async def my_command(self, ctx):
        user = await self.entity_helper.get_or_fetch_user(123)
        await self.taco_helper.give_tacos(ctx.guild.id, ctx.author, user, "Good job!", tacotypes.TacoTypes.CUSTOM, 5)
        response = await self.prompt_helper.ask_text(ctx, ctx.channel, "What's your favorite color?")
```

---

## Which Helper Do I Need?

Use this quick reference:

| Task | Use This Helper |
|------|-----------------|
| Get a user/member/role/channel | `EntityHelper` |
| Ask user for input (yes/no, text, number, selection) | `PromptHelper` |
| Give tacos or log taco events | `TacoHelper` |
| Move a message or notify about bot initialization | `MessageHelper` |
| Add/remove roles in bulk | `RoleHelper` |
| Create test context objects | `ContextHelper` |

---

## Timeline

| Phase | What's Happening | Duration |
|-------|------------------|----------|
| **Phase 1** | Create EntityHelper, RoleHelper, ContextHelper | Week 1 |
| **Phase 2** | Create MessageHelper, TacoHelper | Week 2 |
| **Phase 3** | Create PromptHelper | Week 3 |
| **Phase 4** | Create backward-compatible facade | Week 4 |
| **Phase 5** | Migrate all cogs (30+ files) | Weeks 5-7 |
| **Phase 6** | Migrate HTTP handlers | Week 8 |
| **Phase 7** | Migrate lib utilities | Week 9 |
| **Phase 8** | Final cleanup, documentation, PR | Week 10 |

**Total:** 10 weeks

---

## Benefits

✅ **Easier to find methods** - No scanning 800 lines  
✅ **Easier to test** - Mock only what you need  
✅ **Better organized** - Related functionality grouped together  
✅ **Follows best practices** - Single Responsibility Principle  
✅ **No breaking changes** - Backward-compatible facade maintained  
✅ **Better documentation** - Each helper documented separately  

---

## FAQs

**Q: Do I need to change my existing code right away?**  
A: No! The old `DiscordHelper` will still work via a facade pattern. Migrate at your own pace.

**Q: What if I only need one or two helpers?**  
A: Only import and initialize the helpers you need. No need to use all six.

**Q: Will this affect performance?**  
A: No significant impact. Delegation overhead is negligible compared to Discord API calls.

**Q: When will the old DiscordHelper be removed?**  
A: Not for at least 6-12 months after all code is migrated. Plenty of time for transition.

**Q: What if I find a bug in the new helpers?**  
A: Report it immediately. We have comprehensive tests, but if you find an issue, we'll fix it ASAP.

---

## Getting Help

- Read the full plan: `docs/refactoring/discordhelper_refactoring_plan.md`
- Check helper documentation: `docs/lib/helpers/`
- Ask questions in the project issue tracker
- Contact the project maintainer

---

**Happy refactoring! 🎉**
