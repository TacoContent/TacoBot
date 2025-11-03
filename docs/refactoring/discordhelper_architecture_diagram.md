# DiscordHelper Refactoring - Architecture Diagram

## Current State (Before Refactoring)

``` text
┌─────────────────────────────────────────────────────────────┐
│                      DiscordHelper                          │
│                       (~800 lines)                          │
├─────────────────────────────────────────────────────────────┤
│  Entity Fetching (5 methods)                               │
│  User Prompts (8 methods)                                  │
│  Taco Operations (4 methods)                               │
│  Message Operations (2 methods)                            │
│  Role Management (1 method)                                │
│  Utilities (1 method)                                      │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────┴─────┐  ┌─────┴──────┐  ┌────┴─────┐
    │    Cogs    │  │  Handlers  │  │   Libs   │
    │  (30+)     │  │   (15+)    │  │   (2+)   │
    └────────────┘  └────────────┘  └──────────┘
```

**Problems:**

- Single God Class with too many responsibilities
- Hard to test individual concerns
- Difficult to navigate 800+ lines
- High coupling

---

## Future State (After Refactoring)

``` text
┌──────────────────────────────────────────────────────────────────┐
│                         Helper Layer                             │
├──────────────┬──────────────┬──────────────┬──────────────┬──────┤
│              │              │              │              │      │
│   Entity     │   Prompt     │    Taco      │   Message    │ Role │
│   Helper     │   Helper     │   Helper     │   Helper     │Helper│
│              │              │              │              │      │
│ • get_user   │ • ask_yes_no │ • give_tacos │ • move_msg   │• add │
│ • get_member │ • ask_text   │ • log_tacos  │ • notify     │• rem │
│ • get_role   │ • ask_number │ • purge_log  │              │      │
│ • get_chan   │ • ask_channel│              │              │      │
│              │ • ask_role   │              │              │      │
└──────────────┴──────────────┴──────────────┴──────────────┴──────┘
                           ▲
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────┴─────┐  ┌─────┴──────┐  ┌────┴─────┐
    │    Cogs    │  │  Handlers  │  │   Libs   │
    │  (30+)     │  │   (15+)    │  │   (2+)   │
    │            │  │            │  │          │
    │  Import    │  │  Import    │  │  Import  │
    │  specific  │  │  specific  │  │  specific│
    │  helpers   │  │  helpers   │  │  helpers │
    └────────────┘  └────────────┘  └──────────┘
```

**Benefits:**

- Single Responsibility per helper
- Easy to test in isolation
- Clear organization
- Low coupling

---

## Dependency Graph

``` text
┌──────────────┐
│ContextHelper │  (No dependencies)
└──────────────┘

┌──────────────┐
│ EntityHelper │
└──────┬───────┘
       │ uses
       ▼
  ┌─────────┐
  │   Bot   │
  │ Logger  │
  └─────────┘

┌──────────────┐
│  RoleHelper  │
└──────┬───────┘
       │ uses
       ▼
  ┌─────────┐
  │ Logger  │
  └─────────┘

┌──────────────┐
│MessageHelper │
└──────┬───────┘
       │ uses
       ├─────────┐
       ▼         ▼
  ┌──────────┐ ┌──────────┐
  │Messaging │ │ Settings │
  └──────────┘ └──────────┘

┌──────────────┐
│ TacoHelper   │
└──────┬───────┘
       │ uses
       ├─────────┬─────────────┬──────────────┐
       ▼         ▼             ▼              ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │TacosDB   │ │EntityHelp│ │Messaging │ │ Settings │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘

┌──────────────┐
│PromptHelper  │
└──────┬───────┘
       │ uses
       ├─────────┬─────────────┬──────────────┐
       ▼         ▼             ▼              ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │Messaging │ │EntityHelp│ │ Settings │ │   Bot    │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘
               (for lookups)              (for wait_for)
```

**Dependency Rules:**

1. ✅ Helpers can depend on other helpers (one-way, no cycles)
2. ✅ Helpers can depend on shared services (Bot, Logger, Settings, Messaging)
3. ❌ Helpers should NOT depend on Cogs or Handlers
4. ❌ No circular dependencies between helpers

---

## File Structure

``` text
bot/lib/
├── helpers/
│   ├── __init__.py                 # Exports all helpers
│   ├── context_helper.py           # ContextHelper
│   ├── entity_helper.py            # EntityHelper
│   ├── role_helper.py              # RoleHelper
│   ├── message_helper.py           # MessageHelper
│   ├── taco_helper.py              # TacoHelper
│   └── prompt_helper.py            # PromptHelper
├── discordhelper.py                # DEPRECATED: Legacy facade
├── messaging.py                    # Used by multiple helpers
├── settings.py                     # Used by multiple helpers
└── logger.py                       # Used by multiple helpers

tests/lib/
├── helpers/
│   ├── test_context_helper.py
│   ├── test_entity_helper.py
│   ├── test_role_helper.py
│   ├── test_message_helper.py
│   ├── test_taco_helper.py
│   └── test_prompt_helper.py
└── test_discordhelper_facade.py    # Integration tests
```

---

## Data Flow Examples

### Example 1: Giving Tacos

``` text
User runs /give @user 5 tacos

       │
       ▼
┌────────────┐
│ Tacos Cog  │
└─────┬──────┘
      │
      │ calls give_tacos()
      ▼
┌──────────────┐
│  TacoHelper  │◄─── gets taco settings from Settings
└──────┬───────┘
       │ needs to log to channel
       │
       │ calls get_or_fetch_channel()
       ▼
┌──────────────┐
│EntityHelper  │◄─── fetches from Discord API via Bot
└──────┬───────┘
       │
       │ returns channel
       ▼
┌──────────────┐
│  TacoHelper  │
└──────┬───────┘
       │ uses Messaging to send log embed
       │ saves to TacosDB
       ▼
   Success!
```

### Example 2: Prompting User for Input

``` text
Cog needs user to select a channel

       │
       ▼
┌────────────┐
│   Any Cog  │
└─────┬──────┘
      │
      │ calls ask_channel()
      ▼
┌──────────────┐
│PromptHelper  │
└──────┬───────┘
       │ sends embed via Messaging
       │ waits for interaction via Bot.wait_for()
       │
       │ user enters custom channel name
       │ needs to look up by name
       │
       │ calls get_by_name_or_id()
       ▼
┌──────────────┐
│EntityHelper  │◄─── looks up channel by name
└──────┬───────┘
       │
       │ returns channel
       ▼
┌──────────────┐
│PromptHelper  │
└──────┬───────┘
       │ invokes callback with channel
       ▼
┌────────────┐
│   Any Cog  │
└────────────┘
  Receives channel and continues
```

### Example 3: Moving a Message

``` text
Moderator uses /move command

       │
       ▼
┌────────────────┐
│ MoveMessage Cog│
└─────┬──────────┘
      │
      │ calls move_message()
      ▼
┌──────────────┐
│MessageHelper │
└──────┬───────┘
       │ extracts embed fields
       │ creates new embed
       │ sends to target channel via Messaging
       │ optionally deletes original
       ▼
   Message moved!
```

---

## Migration Flow

``` text
Phase 1 (Week 1)
┌──────────────────────────────────────┐
│ Create Base Helpers                  │
│  • ContextHelper                     │
│  • EntityHelper                      │
│  • RoleHelper                        │
│                                      │
│ Status: New code, no migration yet   │
└──────────────────────────────────────┘

Phase 2 (Week 2)
┌──────────────────────────────────────┐
│ Create Mid-Level Helpers             │
│  • MessageHelper                     │
│  • TacoHelper                        │
│                                      │
│ Status: New code, no migration yet   │
└──────────────────────────────────────┘

Phase 3 (Week 3)
┌──────────────────────────────────────┐
│ Create Complex Helper                │
│  • PromptHelper                      │
│                                      │
│ Status: All helpers ready            │
└──────────────────────────────────────┘

Phase 4 (Week 4)
┌──────────────────────────────────────┐
│ Create Backward Compatibility        │
│  • Modify DiscordHelper to facade    │
│  • Delegate all methods              │
│                                      │
│ Status: Old code still works         │
└──────────────────────────────────────┘

Phase 5-7 (Weeks 5-9)
┌──────────────────────────────────────┐
│ Migrate Existing Code                │
│  Week 5-7: Cogs (30+ files)          │
│  Week 8:   HTTP Handlers (15+ files) │
│  Week 9:   Lib utilities (2+ files)  │
│                                      │
│ Status: Progressive migration        │
└──────────────────────────────────────┘

Phase 8 (Week 10)
┌──────────────────────────────────────┐
│ Finalize                             │
│  • Add deprecation warnings          │
│  • Complete documentation            │
│  • Create PR                         │
│                                      │
│ Status: Ready for review             │
└──────────────────────────────────────┘

Phase 9 (6-12 months later - Optional)
┌──────────────────────────────────────┐
│ Remove Deprecated Facade             │
│  • Delete discordhelper.py           │
│  • Remove any lingering references   │
│                                      │
│ Status: Clean architecture           │
└──────────────────────────────────────┘
```

---

## Testing Architecture

``` text
Unit Tests (Isolated)
┌──────────────────────────────────────┐
│ test_entity_helper.py                │
│  • Mock: Bot, Logger                 │
│  • Test: All entity fetch methods    │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ test_prompt_helper.py                │
│  • Mock: Bot, Messaging, EntityHelp  │
│  • Test: All prompt methods          │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ test_taco_helper.py                  │
│  • Mock: TacosDB, EntityHelp, Msg    │
│  • Test: Taco operations             │
└──────────────────────────────────────┘

Integration Tests
┌──────────────────────────────────────┐
│ test_discordhelper_facade.py         │
│  • Test: DiscordHelper delegates     │
│  • Test: Backward compatibility      │
│  • Test: Properties accessible       │
└──────────────────────────────────────┘

Regression Tests (Optional)
┌──────────────────────────────────────┐
│ test_discordhelper_regression.py     │
│  • Run old tests against facade      │
│  • Ensure same outputs               │
└──────────────────────────────────────┘
```

---

## Legend

``` text
┌─────┐
│ Box │  = Component/Class/File
└─────┘

   │
   ▼     = Dependency/Flow direction

  ───    = Grouping/Relationship

(text)   = Note/Explanation
```
