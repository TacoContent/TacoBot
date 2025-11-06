# Tacos Cog Testability Improvements

**Document Version:** 1.0  
**Date:** November 5, 2025  
**Target File:** `bot/cogs/tacos.py`  
**Purpose:** Identify and document improvements to enhance testability of the TacosCog

---

## Executive Summary

The `TacosCog` is a critical component of TacoBot that handles taco gifting, counting, and reaction-based rewards. While functional, the current implementation has several characteristics that make comprehensive unit testing challenging. This document outlines specific, actionable improvements to enhance testability while maintaining existing functionality.

**Key Areas of Improvement:**
1. Dependency injection and interface abstraction
2. Method decomposition and single responsibility
3. Testable error handling patterns
4. Discord API interaction isolation
5. Configuration and settings management
6. Time-based logic testability

---

## 1. Dependency Injection & Interface Abstraction

### Current State
- Database dependencies (`tacos_db`, `tracking_db`) are optional parameters but instantiated directly in `__init__` if not provided
- Helper classes (`messaging`, `entity_helper`, `taco_helper`) are instantiated directly without injection
- Direct coupling to concrete implementations makes mocking difficult

### Suggestions

#### 1.1 Full Constructor Injection
**Priority:** High  
**Effort:** Medium

Convert all dependencies to required constructor parameters:

```python
def __init__(
    self,
    bot: TacoBot,
    tacos_db: TacosDatabase,
    tracking_db: TrackingDatabase,
    messaging: Messaging,
    entity_helper: EntityHelper,
    taco_helper: TacoHelper,
) -> None:
```

**Benefits:**
- Explicit dependencies visible in constructor
- Forces test setup to provide all dependencies (no hidden instantiation)
- Makes mocking straightforward
- Eliminates conditional logic in constructor

**Implementation Notes:**
- Update cog loader in `setup()` function to instantiate all dependencies
- Consider creating a factory method or builder if dependency graph becomes complex
- Add type hints for all injected dependencies

#### 1.2 Protocol/Interface Definitions
**Priority:** Medium  
**Effort:** High

Create protocol definitions for database and helper interfaces:

```python
# bot/lib/protocols/tacos_database_protocol.py
from typing import Protocol

class TacosDatabaseProtocol(Protocol):
    def get_tacos_count(self, guild_id: int, user_id: int) -> int: ...
    def remove_all_tacos(self, guild_id: int, user_id: int) -> None: ...
    def add_taco_gift(self, guild_id: int, user_id: int, amount: int) -> None: ...
    def get_total_gifted_tacos(self, guild_id: int, user_id: int, timespan: int) -> int: ...
    def get_taco_reaction(self, guild_id: int, user_id: int, channel_id: int, message_id: int) -> bool: ...
    def add_taco_reaction(self, guild_id: int, user_id: int, channel_id: int, message_id: int) -> None: ...
```

**Benefits:**
- Type-safe mocking with proper IDE support
- Clear contract definition for what the cog needs
- Easier to create test doubles that match expected behavior
- Documentation of required database operations

---

## 2. Method Decomposition & Single Responsibility

### Current State
- Methods like `gift()` and `gift_interaction()` contain complex business logic mixed with presentation logic
- Validation, calculation, and action are intertwined
- Duplicate logic between command and interaction variants

### Suggestions

#### 2.1 Extract Business Logic Methods
**Priority:** High  
**Effort:** Medium

Create pure business logic methods that can be tested independently:

```python
def _validate_gift_eligibility(
    self,
    guild_id: int,
    giver_id: int,
    receiver_id: int,
    amount: int,
    max_gift_tacos: int,
    max_gift_taco_timespan: int,
) -> tuple[bool, str | None]:
    """
    Validates if a user can gift tacos.
    
    Returns:
        tuple[bool, str | None]: (is_valid, error_message)
    """
    # Self-gift check
    if giver_id == receiver_id:
        return False, "taco_self_gift_message"
    
    # Calculate remaining gifts
    total_gifted = self.tacos_db.get_total_gifted_tacos(
        guild_id, giver_id, max_gift_taco_timespan
    )
    remaining_gifts = max_gift_tacos - total_gifted
    
    # Check limits
    if remaining_gifts <= 0:
        return False, "taco_gift_maximum"
    
    if amount <= 0 or amount > remaining_gifts:
        return False, "taco_gift_limit_exceeded"
    
    return True, None
```

**Benefits:**
- Testable without Discord context
- Can test all validation paths independently
- Reusable between command and interaction handlers
- Clear input/output contract

#### 2.2 Extract Presentation Logic
**Priority:** Medium  
**Effort:** Low

Create helper methods for message formatting:

```python
def _format_gift_success_message(
    self,
    guild_id: int,
    giver_mention: str,
    receiver_mention: str,
    amount: int,
    reason: str,
) -> str:
    """Formats the gift success message."""
    tacos_word = self.settings.get_string(guild_id, "taco_singular")
    if amount > 1:
        tacos_word = self.settings.get_string(guild_id, "taco_plural")
    
    return self.settings.get_string(
        guild_id,
        "taco_gift_success",
        user=giver_mention,
        touser=receiver_mention,
        amount=amount,
        taco_word=tacos_word,
        reason=reason,
    )
```

**Benefits:**
- Testable message formatting logic
- Consistent message format across commands
- Easy to verify pluralization logic
- Separates concerns (business vs presentation)

#### 2.3 Consolidate Duplicate Logic
**Priority:** High  
**Effort:** Medium

Both `gift()` and `gift_interaction()` have nearly identical logic. Create a core method:

```python
async def _process_gift(
    self,
    guild_id: int,
    giver: discord.User | discord.Member,
    receiver: discord.Member,
    amount: int,
    reason: str | None,
) -> tuple[bool, str]:
    """
    Core gift processing logic.
    
    Returns:
        tuple[bool, str]: (success, message_key_or_text)
    """
    # All validation and processing logic here
    # Returns result that calling method formats appropriately
```

**Benefits:**
- Single source of truth for gift logic
- Changes only need to be made once
- Tests cover both command variants
- Reduces maintenance burden

---

## 3. Testable Error Handling

### Current State
- Try-catch blocks catch `Exception` (too broad)
- Error handling mixed with business logic
- Difficult to test error paths without triggering actual exceptions

### Suggestions

#### 3.1 Specific Exception Types
**Priority:** Medium  
**Effort:** Low

Define custom exceptions for predictable error cases:

```python
# bot/lib/exceptions/taco_exceptions.py
class TacoException(Exception):
    """Base exception for taco operations."""
    pass

class TacoSelfGiftException(TacoException):
    """Raised when user attempts to gift tacos to themselves."""
    pass

class TacoGiftLimitException(TacoException):
    """Raised when user exceeds gift limits."""
    def __init__(self, remaining: int):
        self.remaining = remaining
        super().__init__(f"Gift limit exceeded. Remaining: {remaining}")

class TacoInsufficientFundsException(TacoException):
    """Raised when user doesn't have enough tacos."""
    def __init__(self, current: int, required: int):
        self.current = current
        self.required = required
        super().__init__(f"Insufficient tacos: {current}/{required}")
```

**Benefits:**
- Testable error conditions without triggering database failures
- Semantic exception types improve code clarity
- Can test exception handling independently
- Better error messages for debugging

#### 3.2 Error Handling Strategy Pattern
**Priority:** Low  
**Effort:** Medium

Separate error handling from business logic:

```python
class ErrorHandler:
    """Handles error responses for taco operations."""
    
    async def handle_command_error(
        self,
        ctx: commands.Context,
        error: Exception,
        delete_after: int = 30,
    ) -> None:
        """Handle errors from prefix commands."""
        # Error handling logic here
    
    async def handle_interaction_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
    ) -> None:
        """Handle errors from slash commands."""
        # Error handling logic here
```

**Benefits:**
- Testable error responses
- Consistent error handling across commands
- Easy to verify correct error messages are sent
- Separates concerns

---

## 4. Discord API Interaction Isolation

### Current State
- Direct Discord API calls throughout methods
- Tightly coupled to Discord.py objects
- Difficult to test without mocking entire Discord context

### Suggestions

#### 4.1 Discord Adapter Layer
**Priority:** High  
**Effort:** High

Create an adapter that wraps Discord interactions:

```python
# bot/lib/adapters/discord_adapter.py
from typing import Protocol

class DiscordAdapterProtocol(Protocol):
    async def send_message(
        self,
        channel_id: int,
        content: str,
        embed: dict | None = None,
        ephemeral: bool = False,
    ) -> None: ...
    
    async def delete_message(self, message_id: int) -> None: ...
    
    async def fetch_message(
        self,
        channel_id: int,
        message_id: int,
    ) -> dict: ...

class RealDiscordAdapter:
    """Real implementation that calls Discord API."""
    
    async def send_message(self, channel_id: int, content: str, **kwargs) -> None:
        channel = await self.bot.fetch_channel(channel_id)
        await channel.send(content, **kwargs)

class MockDiscordAdapter:
    """Test implementation that records calls."""
    
    def __init__(self):
        self.sent_messages = []
        self.deleted_messages = []
    
    async def send_message(self, channel_id: int, content: str, **kwargs) -> None:
        self.sent_messages.append({
            'channel_id': channel_id,
            'content': content,
            **kwargs
        })
```

**Benefits:**
- Test without actual Discord API calls
- Verify messages are sent with correct content
- Fast test execution
- Can simulate Discord failures

#### 4.2 Extract Discord Context Dependencies
**Priority:** Medium  
**Effort:** Medium

Methods should accept data types, not Discord objects:

```python
# Instead of:
async def gift(self, ctx, member: discord.Member, amount: int, reason: str | None) -> None:
    guild_id = ctx.guild.id
    # ...

# Use:
async def gift(self, ctx, member: discord.Member, amount: int, reason: str | None) -> None:
    await self._execute_gift(
        guild_id=ctx.guild.id,
        channel_id=ctx.channel.id,
        giver_id=ctx.author.id,
        giver_mention=ctx.author.mention,
        receiver_id=member.id,
        receiver_mention=member.mention,
        amount=amount,
        reason=reason,
    )

async def _execute_gift(
    self,
    guild_id: int,
    channel_id: int,
    giver_id: int,
    giver_mention: str,
    receiver_id: int,
    receiver_mention: str,
    amount: int,
    reason: str | None,
) -> None:
    """Execute gift with primitive types - easily testable."""
    # All logic here
```

**Benefits:**
- Test with simple data types
- No need to mock complex Discord objects
- Clear data dependencies
- Faster test execution

---

## 5. Configuration & Settings Management

### Current State
- Settings accessed via `self.settings.get_string()` throughout methods
- Taco settings fetched with `self.get_tacos_settings()` (inherited method)
- Hard to test with different configurations
- Magic strings for setting keys

### Suggestions

#### 5.1 Configuration Value Objects
**Priority:** Medium  
**Effort:** Medium

Create typed configuration objects:

```python
# bot/lib/models/taco_config.py
from dataclasses import dataclass

@dataclass
class TacoGiftConfig:
    """Configuration for taco gift operations."""
    max_gift_tacos: int = 10
    max_gift_taco_timespan: int = 86400
    reaction_count: int = 1
    reaction_reward_count: int = 1
    reaction_emojis: list[str] = field(default_factory=lambda: ["🌮"])
    
    @classmethod
    def from_settings(cls, settings_dict: dict) -> "TacoGiftConfig":
        """Create config from settings dictionary."""
        return cls(
            max_gift_tacos=settings_dict.get("max_gift_tacos", 10),
            max_gift_taco_timespan=settings_dict.get("max_gift_taco_timespan", 86400),
            reaction_count=settings_dict.get("reaction_count", 1),
            reaction_reward_count=settings_dict.get("reaction_reward_count", 1),
            reaction_emojis=settings_dict.get("reaction_emojis", ["🌮"]),
        )

@dataclass
class TacoMessages:
    """Localized messages for taco operations."""
    self_gift_error: str
    gift_success: str
    gift_maximum: str
    gift_limit_exceeded: str
    reason_default: str
    # ... etc
    
    @classmethod
    def from_settings(cls, settings, guild_id: int) -> "TacoMessages":
        """Load messages from settings."""
        return cls(
            self_gift_error=settings.get_string(guild_id, "taco_self_gift_message"),
            gift_success=settings.get_string(guild_id, "taco_gift_success"),
            # ... etc
        )
```

**Benefits:**
- Type-safe configuration access
- Easy to create test configurations
- Clear documentation of all config values
- IDE autocomplete for config properties
- Can validate configuration values

#### 5.2 Configuration Injection
**Priority:** Medium  
**Effort:** Low

Pass configuration to methods instead of loading internally:

```python
async def _process_gift(
    self,
    guild_id: int,
    giver_id: int,
    receiver_id: int,
    amount: int,
    config: TacoGiftConfig,  # Injected
) -> tuple[bool, str | None]:
    """Process gift with provided configuration."""
    # Use config.max_gift_tacos instead of loading settings
```

**Benefits:**
- Test with different configurations easily
- No database/settings dependency in business logic
- Clear what configuration affects behavior
- Can test edge cases with extreme config values

---

## 6. Time-Based Logic Testability

### Current State
- Time-based logic (24-hour gift limits) uses implicit current time
- `max_gift_taco_timespan` used for lookback period
- Cannot test time-dependent behavior without waiting

### Suggestions

#### 6.1 Clock Abstraction
**Priority:** Medium  
**Effort:** Low

Create a clock interface for time operations:

```python
# bot/lib/utils/clock.py
from datetime import datetime
from typing import Protocol

class ClockProtocol(Protocol):
    def now(self) -> datetime: ...
    def timestamp(self) -> int: ...

class SystemClock:
    """Uses real system time."""
    def now(self) -> datetime:
        return datetime.now()
    
    def timestamp(self) -> int:
        return int(datetime.now().timestamp())

class MockClock:
    """Controllable clock for testing."""
    def __init__(self, fixed_time: datetime):
        self._time = fixed_time
    
    def now(self) -> datetime:
        return self._time
    
    def timestamp(self) -> int:
        return int(self._time.timestamp())
    
    def advance(self, seconds: int) -> None:
        """Advance time for testing."""
        self._time += timedelta(seconds=seconds)
```

**Benefits:**
- Test time-based logic without waiting
- Simulate different timespan scenarios
- Test edge cases (exactly at limit, one second over, etc.)
- Fast, deterministic tests

#### 6.2 Time-Aware Method Signatures
**Priority:** Low  
**Effort:** Low

Accept timestamp parameters for time-sensitive operations:

```python
def get_total_gifted_tacos(
    self,
    guild_id: int,
    user_id: int,
    timespan: int,
    current_time: int | None = None,  # Optional for testing
) -> int:
    """Get total gifted tacos within timespan."""
    if current_time is None:
        current_time = int(datetime.now().timestamp())
    # Use current_time in calculation
```

**Benefits:**
- Test with specific timestamps
- Verify boundary conditions
- No need to mock datetime globally
- Backward compatible (None = use real time)

---

## 7. Event Handler Testability

### Current State
- `on_message()` and `on_raw_reaction_add()` are large, complex methods
- Mix event parsing, validation, and business logic
- Difficult to test individual aspects

### Suggestions

#### 7.1 Decompose Event Handlers
**Priority:** High  
**Effort:** Medium

Break event handlers into testable components:

```python
async def on_message(self, message: discord.Message) -> None:
    """Main event handler - delegates to specific handlers."""
    if not self._should_process_message(message):
        return
    
    if message.type == discord.MessageType.premium_guild_subscription:
        await self._handle_boost_message(message)
    elif message.type == discord.MessageType.default:
        await self._handle_reply_message(message)

def _should_process_message(self, message: discord.Message) -> bool:
    """Testable validation logic."""
    if not message.guild:
        return False
    if not message.author or message.author.bot or message.author.system:
        return False
    return True

async def _handle_boost_message(self, message: discord.Message) -> None:
    """Testable boost handling."""
    # Just the boost logic

async def _handle_reply_message(self, message: discord.Message) -> None:
    """Testable reply handling."""
    # Just the reply logic
```

**Benefits:**
- Test validation logic separately
- Test each event type independently
- Can mock only what specific handler needs
- Easier to understand what each handler does

#### 7.2 Event Data Objects
**Priority:** Low  
**Effort:** Medium

Create data objects from Discord events:

```python
@dataclass
class ReactionEventData:
    """Normalized reaction event data."""
    guild_id: int
    channel_id: int
    message_id: int
    user_id: int
    emoji: str
    event_type: str
    
    @classmethod
    def from_payload(cls, payload) -> "ReactionEventData":
        """Create from Discord payload."""
        return cls(
            guild_id=payload.guild_id,
            channel_id=payload.channel_id,
            message_id=payload.message_id,
            user_id=payload.user_id,
            emoji=str(payload.emoji),
            event_type=payload.event_type,
        )

async def on_raw_reaction_add(self, payload) -> None:
    """Event entry point."""
    event_data = ReactionEventData.from_payload(payload)
    await self._process_reaction(event_data)

async def _process_reaction(self, event: ReactionEventData) -> None:
    """Testable with simple data object."""
    # All logic here, uses event.guild_id, event.emoji, etc.
```

**Benefits:**
- Test with simple data structures
- No Discord.py dependencies in tests
- Clear data contract
- Can create test fixtures easily

---

## 8. Testing Infrastructure Suggestions

### 8.1 Test Fixtures
**Priority:** High  
**Effort:** Medium

Create reusable fixtures for common test scenarios:

```python
# tests/fixtures/tacos_fixtures.py
import pytest
from tests.mocks.mock_tacos_db import MockTacosDatabase
from tests.mocks.mock_tracking_db import MockTrackingDatabase

@pytest.fixture
def mock_tacos_db():
    """Provides a mock tacos database."""
    return MockTacosDatabase()

@pytest.fixture
def mock_tracking_db():
    """Provides a mock tracking database."""
    return MockTrackingDatabase()

@pytest.fixture
def taco_config():
    """Default taco configuration for tests."""
    return TacoGiftConfig(
        max_gift_tacos=10,
        max_gift_taco_timespan=86400,
        reaction_count=1,
        reaction_emojis=["🌮"],
    )

@pytest.fixture
def tacos_cog(mock_bot, mock_tacos_db, mock_tracking_db):
    """Provides a fully configured TacosCog for testing."""
    return TacosCog(
        bot=mock_bot,
        tacos_db=mock_tacos_db,
        tracking_db=mock_tracking_db,
        # ... other dependencies
    )
```

### 8.2 Mock Implementations
**Priority:** High  
**Effort:** High

Create comprehensive mock implementations:

```python
# tests/mocks/mock_tacos_db.py
class MockTacosDatabase:
    """Mock implementation of TacosDatabase for testing."""
    
    def __init__(self):
        self.tacos: dict[tuple[int, int], int] = {}  # (guild_id, user_id) -> count
        self.gifts: dict[tuple[int, int], list[int]] = {}  # (guild_id, user_id) -> [timestamps]
        self.reactions: set[tuple[int, int, int, int]] = set()  # (guild, user, channel, message)
    
    def get_tacos_count(self, guild_id: int, user_id: int) -> int:
        return self.tacos.get((guild_id, user_id), 0)
    
    def add_taco_gift(self, guild_id: int, user_id: int, amount: int) -> None:
        key = (guild_id, user_id)
        if key not in self.gifts:
            self.gifts[key] = []
        self.gifts[key].append(amount)
    
    def get_total_gifted_tacos(
        self,
        guild_id: int,
        user_id: int,
        timespan: int,
    ) -> int:
        key = (guild_id, user_id)
        return sum(self.gifts.get(key, []))
    
    # ... other methods
```

### 8.3 Test Categories
**Priority:** Medium  
**Effort:** Low

Organize tests by category for clarity:

```
tests/
  unit/
    cogs/
      test_tacos_business_logic.py  # Pure business logic tests
      test_tacos_validation.py       # Validation logic tests
      test_tacos_formatting.py       # Message formatting tests
  integration/
    cogs/
      test_tacos_gift_flow.py        # Full gift flow tests
      test_tacos_reaction_flow.py    # Full reaction flow tests
  e2e/
    test_tacos_scenarios.py          # End-to-end scenarios
```

**Benefits:**
- Clear test organization
- Can run specific test categories
- Easier to identify coverage gaps
- Faster feedback (unit tests run quickly)

---

## 9. Specific Method-Level Suggestions

### 9.1 `remove_all_tacos()` / `_remove_all_tacos_interaction()`

**Current Issues:**
- Direct database call
- Mixed logging and error handling
- Duplicate logic between variants

**Improvements:**
```python
def _validate_purge_permission(self, executor_id: int, target_id: int) -> bool:
    """Validate purge permissions (extendable for future rules)."""
    return True  # Currently admin-only via decorator

async def _execute_purge(
    self,
    guild_id: int,
    target_user_id: int,
    executor_user_id: int,
    reason: str,
) -> None:
    """Core purge logic - fully testable."""
    self.tacos_db.remove_all_tacos(guild_id, target_user_id)
    await self.taco_helper.log_taco_purge(
        guild_id,
        target_user_id,
        executor_user_id,
        reason,
    )
```

**Testing Benefits:**
- Test purge without Discord context
- Verify logging is called correctly
- Test with various reason strings

### 9.2 `gift()` / `gift_interaction()`

**Current Issues:**
- Complex validation mixed with presentation
- Duplicate code
- Hard to test individual validation rules

**Improvements:**
```python
class GiftValidationResult:
    """Result of gift validation."""
    def __init__(self, valid: bool, error_key: str | None = None, **context):
        self.valid = valid
        self.error_key = error_key
        self.context = context

async def _validate_gift(
    self,
    guild_id: int,
    giver_id: int,
    receiver_id: int,
    amount: int,
) -> GiftValidationResult:
    """Validate gift operation."""
    # Self-gift check
    if giver_id == receiver_id:
        return GiftValidationResult(False, "taco_self_gift_message")
    
    # Amount check
    if amount <= 0:
        return GiftValidationResult(False, "taco_invalid_amount")
    
    # Load config once
    config = self._load_gift_config(guild_id)
    
    # Limit check
    total_gifted = self.tacos_db.get_total_gifted_tacos(
        guild_id, giver_id, config.max_gift_taco_timespan
    )
    remaining = config.max_gift_tacos - total_gifted
    
    if remaining <= 0:
        return GiftValidationResult(
            False,
            "taco_gift_maximum",
            max=config.max_gift_tacos,
        )
    
    if amount > remaining:
        return GiftValidationResult(
            False,
            "taco_gift_limit_exceeded",
            remaining=remaining,
        )
    
    return GiftValidationResult(True)
```

**Testing Benefits:**
- Test each validation rule independently
- Test boundary conditions easily
- Clear validation result contract
- Can test without database

### 9.3 `on_raw_reaction_add()`

**Current Issues:**
- Very long method (80+ lines)
- Multiple responsibilities
- Complex nested conditions
- Hard to test specific scenarios

**Improvements:**
```python
async def on_raw_reaction_add(self, payload) -> None:
    """Entry point for reaction events."""
    # Quick validation
    if payload.event_type != 'REACTION_ADD':
        return
    
    event_data = ReactionEventData.from_payload(payload)
    
    # Early exits
    if not await self._should_process_reaction(event_data):
        return
    
    await self._process_taco_reaction(event_data)

async def _should_process_reaction(self, event: ReactionEventData) -> bool:
    """Determine if reaction should be processed."""
    # Check emoji
    config = self._load_gift_config(event.guild_id)
    if event.emoji not in config.reaction_emojis:
        return False
    
    # Check user
    user = await self.entity_helper.get_or_fetch_user(event.user_id)
    if not user or user.bot or user.system:
        return False
    
    # Check message author
    message = await self._fetch_message(event.channel_id, event.message_id)
    if not message or message.author.bot or message.author.id == event.user_id:
        return False
    
    # Check if already reacted
    if self.tacos_db.get_taco_reaction(
        event.guild_id, event.user_id, event.channel_id, event.message_id
    ):
        return False
    
    return True

async def _process_taco_reaction(self, event: ReactionEventData) -> None:
    """Process validated taco reaction."""
    config = self._load_gift_config(event.guild_id)
    message = await self._fetch_message(event.channel_id, event.message_id)
    user = await self.entity_helper.get_or_fetch_user(event.user_id)
    
    # Track reaction
    self.tacos_db.add_taco_reaction(
        event.guild_id, event.user_id, event.channel_id, event.message_id
    )
    
    # Give reward to message author
    await self.taco_helper.give_tacos(
        event.guild_id,
        user,
        message.author,
        self.settings.get_string(event.guild_id, "taco_reason_react", user=message.author.name),
        tacotypes.TacoTypes.REACT_REWARD,
    )
    
    # Check if giver should also receive tacos
    await self._process_reaction_giver_reward(event, config, user, message)
```

**Testing Benefits:**
- Test validation logic separately from processing
- Test each early-exit condition independently
- Mock only what each component needs
- Clear separation of concerns

---

## 10. Implementation Roadmap

### Phase 1: Foundation (High Priority, Low Risk)
**Estimated Effort:** 2-3 days

1. Add custom exception types
2. Create configuration value objects
3. Extract message formatting methods
4. Add mock database implementations
5. Create basic test fixtures

**Rationale:** These changes are low-risk, don't affect existing functionality, and provide immediate testing benefits.

### Phase 2: Method Decomposition (High Priority, Medium Risk)
**Estimated Effort:** 3-4 days

1. Extract validation methods
2. Consolidate duplicate command/interaction logic
3. Break down event handlers
4. Add unit tests for new methods

**Rationale:** Improves testability significantly while maintaining existing behavior. Requires careful refactoring but is well-scoped.

### Phase 3: Dependency Injection (Medium Priority, Medium Risk)
**Estimated Effort:** 2-3 days

1. Add protocol definitions
2. Update constructor for full injection
3. Update cog loader
4. Refactor tests to use new injection pattern

**Rationale:** Makes testing much easier but requires coordinated changes across multiple files.

### Phase 4: Discord Abstraction (Medium Priority, High Effort)
**Estimated Effort:** 5-7 days

1. Create Discord adapter interface
2. Implement real and mock adapters
3. Refactor methods to use adapter
4. Update all tests

**Rationale:** Largest improvement to testability but most invasive change. Consider if benefits justify effort.

### Phase 5: Advanced Testing (Low Priority, Ongoing)
**Estimated Effort:** Ongoing

1. Add clock abstraction for time-based tests
2. Create comprehensive integration tests
3. Add end-to-end test scenarios
4. Achieve >90% code coverage

**Rationale:** Polish and completeness. Can be done incrementally as other phases complete.

---

## 11. Success Metrics

### Code Coverage
- **Current:** Unknown (needs baseline measurement)
- **Target Phase 1:** 40%
- **Target Phase 2:** 60%
- **Target Phase 3:** 75%
- **Target Phase 5:** 90%+

### Test Execution Speed
- **Target:** Unit tests complete in <5 seconds
- **Target:** Full test suite completes in <30 seconds

### Test Independence
- **Target:** All tests can run in any order
- **Target:** No external dependencies (database, Discord API) in unit tests

### Maintenance Metrics
- **Target:** New features come with tests (100% of PRs)
- **Target:** Bug fixes include regression tests (100% of bug PRs)
- **Target:** No duplicate test code (DRY principle)

---

## 12. Testing Examples

### Example: Testing Gift Validation

**After implementing suggestions:**

```python
# tests/unit/cogs/test_tacos_validation.py
import pytest
from bot.lib.models.taco_config import TacoGiftConfig

class TestGiftValidation:
    """Test gift validation logic."""
    
    @pytest.fixture
    def cog(self, mock_bot, mock_tacos_db):
        return TacosCog(bot=mock_bot, tacos_db=mock_tacos_db)
    
    def test_self_gift_rejected(self, cog):
        """User cannot gift tacos to themselves."""
        result = await cog._validate_gift(
            guild_id=123,
            giver_id=456,
            receiver_id=456,  # Same as giver
            amount=5,
        )
        
        assert not result.valid
        assert result.error_key == "taco_self_gift_message"
    
    def test_negative_amount_rejected(self, cog):
        """Cannot gift negative tacos."""
        result = await cog._validate_gift(
            guild_id=123,
            giver_id=456,
            receiver_id=789,
            amount=-5,
        )
        
        assert not result.valid
        assert result.error_key == "taco_invalid_amount"
    
    def test_exceeds_remaining_gifts_rejected(self, cog, mock_tacos_db):
        """Cannot gift more than remaining limit."""
        # Setup: User has already gifted 8 tacos (limit is 10)
        mock_tacos_db.gifts[(123, 456)] = [8]
        
        result = await cog._validate_gift(
            guild_id=123,
            giver_id=456,
            receiver_id=789,
            amount=5,  # Would exceed limit
        )
        
        assert not result.valid
        assert result.error_key == "taco_gift_limit_exceeded"
        assert result.context["remaining"] == 2
    
    def test_valid_gift_accepted(self, cog):
        """Valid gift passes validation."""
        result = await cog._validate_gift(
            guild_id=123,
            giver_id=456,
            receiver_id=789,
            amount=5,
        )
        
        assert result.valid
        assert result.error_key is None
```

### Example: Testing Message Formatting

```python
# tests/unit/cogs/test_tacos_formatting.py
class TestMessageFormatting:
    """Test message formatting logic."""
    
    def test_singular_taco_word(self, cog):
        """Uses singular 'taco' for amount of 1."""
        msg = cog._format_gift_success_message(
            guild_id=123,
            giver_mention="@alice",
            receiver_mention="@bob",
            amount=1,
            reason="great help",
        )
        
        assert "1 taco" in msg.lower()
        assert "tacos" not in msg.lower()
    
    def test_plural_taco_word(self, cog):
        """Uses plural 'tacos' for amount > 1."""
        msg = cog._format_gift_success_message(
            guild_id=123,
            giver_mention="@alice",
            receiver_mention="@bob",
            amount=5,
            reason="great help",
        )
        
        assert "5 tacos" in msg.lower()
```

### Example: Testing Reaction Processing

```python
# tests/unit/cogs/test_tacos_reactions.py
class TestReactionProcessing:
    """Test reaction event processing."""
    
    def test_wrong_emoji_ignored(self, cog):
        """Non-taco emoji reactions are ignored."""
        event = ReactionEventData(
            guild_id=123,
            channel_id=456,
            message_id=789,
            user_id=111,
            emoji="👍",  # Not a taco
            event_type="REACTION_ADD",
        )
        
        result = await cog._should_process_reaction(event)
        assert not result
    
    def test_bot_reaction_ignored(self, cog, mock_entity_helper):
        """Bot reactions are ignored."""
        mock_entity_helper.set_user_bot(111, is_bot=True)
        
        event = ReactionEventData(
            guild_id=123,
            channel_id=456,
            message_id=789,
            user_id=111,
            emoji="🌮",
            event_type="REACTION_ADD",
        )
        
        result = await cog._should_process_reaction(event)
        assert not result
    
    def test_duplicate_reaction_ignored(self, cog, mock_tacos_db):
        """Same user cannot react twice to same message."""
        # User already reacted
        mock_tacos_db.reactions.add((123, 111, 456, 789))
        
        event = ReactionEventData(
            guild_id=123,
            channel_id=456,
            message_id=789,
            user_id=111,
            emoji="🌮",
            event_type="REACTION_ADD",
        )
        
        result = await cog._should_process_reaction(event)
        assert not result
```

---

## 13. Additional Recommendations

### Documentation
- Add docstrings to all private methods explaining testing considerations
- Document expected behavior for edge cases
- Include examples of test usage in method docstrings

### Continuous Integration
- Run tests on every PR
- Require minimum code coverage (start at 60%, increase over time)
- Run linting to enforce code quality
- Add test performance monitoring

### Refactoring Safety
- Use feature flags for major refactoring
- Keep old and new code paths temporarily during migration
- Add integration tests before refactoring to catch regressions
- Refactor incrementally (one method at a time)

### Team Practices
- Require tests for all new features
- Require regression tests for all bug fixes
- Code review checklist includes testability review
- Pair programming for complex refactoring

---

## 14. Potential Risks & Mitigation

### Risk: Breaking Existing Functionality
**Mitigation:**
- Add integration tests before refactoring
- Refactor in small, reviewable chunks
- Use feature flags for large changes
- Keep old code paths until new ones are verified

### Risk: Increased Complexity
**Mitigation:**
- Follow YAGNI principle (don't over-engineer)
- Start with high-value, low-complexity improvements
- Document architectural decisions
- Regular code reviews to catch complexity creep

### Risk: Time Investment
**Mitigation:**
- Prioritize improvements by value/effort ratio
- Implement in phases (can stop after any phase)
- Measure test coverage improvements to show value
- Automate what can be automated (test generation tools)

### Risk: Incomplete Test Coverage
**Mitigation:**
- Set realistic coverage goals (90% not 100%)
- Focus on critical paths first
- Use mutation testing to verify test quality
- Regular coverage reviews

---

## 15. Conclusion

The TacosCog is a functional, feature-rich component but has significant room for testability improvements. The suggestions in this document range from low-effort quick wins (exception types, message formatting extraction) to high-effort architectural changes (Discord adapter, full dependency injection).

**Recommended Approach:**
1. Start with **Phase 1** (Foundation) - low risk, immediate benefits
2. Measure success with code coverage metrics
3. Proceed to **Phase 2** (Method Decomposition) if Phase 1 is successful
4. Evaluate **Phase 3** and **Phase 4** based on testing pain points discovered

**Key Takeaways:**
- Testability improvements make code more maintainable, not just more testable
- Small, incremental changes are safer than large rewrites
- Focus on separating concerns: business logic, presentation, persistence, Discord API
- Use dependency injection to make components swappable
- Tests should be fast, independent, and clear

This document can serve as a reference for future implementation work, either by you directly or by guiding AI-assisted refactoring in multiple stages.

---

**Document Status:** Ready for Review  
**Next Steps:** Review, prioritize, and begin Phase 1 implementation  
**Questions/Feedback:** [Add notes here during review]
