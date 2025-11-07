# Test Fixture Guidelines

This document explains how to use shared fixtures from `tests/conftest.py` and when to create specialized fixtures.

## Shared Fixtures (conftest.py)

The `tests/conftest.py` file provides commonly-used mock fixtures that are automatically available to all test files. Using these shared fixtures:

- ✅ Reduces code duplication
- ✅ Ensures consistency across tests
- ✅ Makes tests easier to maintain
- ✅ Slightly improves test performance

### Available Shared Fixtures

#### Function-Scoped (Created per test)

| Fixture | Type | Description | Key Features |
|---------|------|-------------|--------------|
| `bot` | `MagicMock` | Discord bot instance | Standard mock bot |
| `settings` | `MagicMock` | Settings manager | `get_settings()`, `get_string()`, `log_level="debug"` |
| `messaging` | `MagicMock` | Messaging helper | `send_embed()`, `notify_of_error()` (AsyncMock) |
| `tacos_db` | `MagicMock` | Tacos database | `get_tacos_count()`, `add_taco_gift()`, `remove_tacos()` |
| `tracking_db` | `MagicMock` | Tracking database | `track_command_usage()`, `track_discord_user()` |
| `announcements_db` | `MagicMock` | Announcements database | `track_announcement()` |
| `twitch_db` | `MagicMock` | Twitch database | `link_twitch_to_discord_from_code()`, `set_twitch_discord_link_code()` |
| `permissions` | `MagicMock` | Permissions handler | `has_taco_permission()` returns `False` by default |
| `entity_helper` | `MagicMock` | Entity helper | Standard mock |
| `taco_helper` | `MagicMock` | Taco helper | Standard mock |
| `message_helper` | `MagicMock` | Message helper | `notify_bot_not_initialized()` (AsyncMock) |
| `prompt_helper` | `MagicMock` | Prompt helper | `ask_yes_no()` (AsyncMock) |

#### Module-Scoped (Created once per test file)

| Fixture | Type | Description |
|---------|------|-------------|
| `module_settings` | `MagicMock` | Shared settings for all tests in module |

#### Session-Scoped (Created once per test session)

| Fixture | Type | Description |
|---------|------|-------------|
| `session_bot` | `MagicMock` | Shared bot for entire test session |

---

## Using Shared Fixtures

### Basic Usage

Simply declare the fixture as a parameter in your test function or fixture:

```python
@pytest.mark.asyncio
async def test_my_feature(bot, settings, messaging):
    """Test using shared fixtures."""
    # No need to create these - they're automatically injected!
    cog = MyCog(bot=bot, settings=settings, messaging=messaging)
    await cog.some_method()
    messaging.send_embed.assert_awaited_once()
```

### Creating a Cog Fixture

Most cog tests need a fixture that creates the cog with injected dependencies:

```python
@pytest.fixture
def cog(bot, settings, tacos_db, messaging):
    """Create MyCog with shared fixtures from conftest.py."""
    c = MyCog(
        bot=bot,
        settings=settings,
        tacos_db=tacos_db,
        messaging=messaging,
    )
    c.log = MagicMock()  # Mock the logger to avoid real logging
    return c
```

**Key points:**
- List all dependencies as parameters
- pytest automatically provides them from `conftest.py`
- No need to create `MagicMock()` instances yourself
- Only override `c.log` to prevent actual logging

---

## When to Create Specialized Fixtures

Create a **local fixture** in your test file when:

### 1. Custom Behavior Required

The shared fixture doesn't match your test's needs:

```python
@pytest.fixture
def mock_settings():
    """Specialized settings with custom get_string behavior."""
    s = MagicMock()
    
    def custom_get_string(*args, **kwargs):
        key = kwargs.get('key')
        if key == "account_link_success_message":
            return f"Success: {kwargs.get('code', '')}"
        elif key == "account_link_unknown_code_message":
            return "Unknown code"
        return "Default message"
    
    s.get_string.side_effect = custom_get_string
    s.log_level = "INFO"
    return s


@pytest.fixture
def cog(bot, messaging, twitch_db, tracking_db, mock_settings):
    """Use specialized mock_settings instead of shared settings."""
    return AccountLinkCog(
        bot=bot,
        messaging=messaging,
        twitch_db=twitch_db,
        tracking_db=tracking_db,
        settings=mock_settings,  # ← Uses local fixture
    )
```

### 2. Test-Specific Mock Objects

Objects that aren't reusable across tests:

```python
@pytest.fixture
def mock_interaction():
    """Discord interaction - only relevant for slash command tests."""
    interaction = MagicMock(spec=Interaction)
    interaction.guild = MagicMock()
    interaction.guild.id = 12345
    interaction.user = MagicMock()
    interaction.user.id = 67890
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    return interaction
```

### 3. Complex Composed Fixtures

Fixtures that combine multiple shared fixtures in a specific way:

```python
@pytest.fixture
def mock_channel_with_history():
    """Channel with message history for import testing."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 123
    
    message1 = MagicMock()
    message1.channel = channel
    message2 = MagicMock()
    message2.channel = channel
    
    async def async_history(limit):
        for msg in [message1, message2]:
            yield msg
    
    channel.history = lambda limit: async_history(limit)
    return channel
```

---

## Best Practices

### ✅ DO

1. **Use shared fixtures by default** - Start with conftest.py fixtures
2. **Override only when necessary** - Keep specialized fixtures minimal
3. **Document specialized behavior** - Add docstrings explaining why custom fixture exists
4. **Use AsyncMock for async methods** - `method = AsyncMock()` for awaitable methods
5. **Name specialized fixtures clearly** - `mock_settings` vs generic `settings`
6. **Keep test-specific fixtures in test file** - Don't add every fixture to conftest.py

### ❌ DON'T

1. **Don't duplicate conftest.py fixtures** - Remove local copies of bot, settings, etc.
2. **Don't use MagicMock for async methods** - Use `AsyncMock()` instead
3. **Don't add highly-specific fixtures to conftest.py** - Keep it general-purpose
4. **Don't forget to document custom behavior** - Future maintainers need context

---

## Migration Checklist

When refactoring tests to use shared fixtures:

- [ ] Remove duplicate fixture definitions (`bot`, `settings`, `messaging`, etc.)
- [ ] Update `cog` fixture to use shared fixtures as parameters
- [ ] Keep specialized fixtures with custom behavior
- [ ] Ensure async methods use `AsyncMock()`
- [ ] Run tests to verify no regressions
- [ ] Update fixture parameter names if needed (e.g., `mock_bot` → `bot`)

---

## Example: Before & After

### Before (Duplicate Fixtures)

```python
from unittest.mock import MagicMock
import pytest
from bot.cogs.my_cog import MyCog


@pytest.fixture
def bot():
    return MagicMock()


@pytest.fixture
def settings():
    s = MagicMock()
    s.get_settings = MagicMock(return_value={})
    s.get_string = MagicMock(return_value="Test string")
    s.name = "TacoBot"
    s.version = "1.0.0"
    s.log_level = "debug"
    return s


@pytest.fixture
def messaging():
    return MagicMock()


@pytest.fixture
def cog(bot, settings, messaging):
    c = MyCog(bot=bot, settings=settings, messaging=messaging)
    c.log = MagicMock()
    return c


def test_my_feature(cog):
    assert cog is not None
```

### After (Shared Fixtures)

```python
from unittest.mock import MagicMock
import pytest
from bot.cogs.my_cog import MyCog


@pytest.fixture
def cog(bot, settings, messaging):
    """Create MyCog with shared fixtures from conftest.py."""
    c = MyCog(bot=bot, settings=settings, messaging=messaging)
    c.log = MagicMock()
    return c


def test_my_feature(cog):
    assert cog is not None
```

**Lines saved:** 20+ lines of duplicate fixture code removed! 🎉

---

## Updating conftest.py

If you find yourself creating the same specialized fixture in multiple test files, consider adding it to `conftest.py`:

1. Ensure it's general-purpose enough for reuse
2. Use descriptive naming
3. Add clear docstring
4. Choose appropriate scope (function, module, session)
5. Add entry to this documentation

---

## Questions?

- **Q: Can I override a shared fixture in my test file?**
  - A: Yes! pytest allows you to redefine fixtures. Your local fixture takes precedence.

- **Q: Should I use `module_settings` or `settings`?**
  - A: Use `settings` (function-scoped) unless you need to share state across all tests in a module. Function-scoped fixtures are isolated and safer.

- **Q: How do I know if a fixture is available?**
  - A: Check `tests/conftest.py` or run `pytest --fixtures` to see all available fixtures.

- **Q: What if I need different default return values?**
  - A: Override the specific method in your test: `settings.get_string.return_value = "Custom"`

---

## See Also

- [pytest fixtures documentation](https://docs.pytest.org/en/stable/fixture.html)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- `tests/conftest.py` - Source of truth for shared fixtures
