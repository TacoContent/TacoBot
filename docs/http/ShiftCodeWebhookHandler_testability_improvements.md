# ShiftCodeWebhookHandler Testability Improvements

## Overview

This document analyzes the `ShiftCodeWebhookHandler.shift_code` method and provides actionable recommendations to improve testability, maintainability, and code quality. The analysis follows the successful pattern established with `MinecraftPlayerWebhookHandler`.

**Current Status:** Monolithic method (~140 lines) with multiple responsibilities  
**Recommendation:** Extract validation, processing, and broadcasting logic into focused helper methods

---

## Current Implementation Analysis

### Method Structure

The `shift_code` method currently handles:

1. ✅ Authentication validation
2. ✅ Request body validation
3. ✅ Payload field validation (games, code)
4. ✅ Code normalization (uppercase, strip spaces)
5. ✅ Expiry checking
6. ✅ Description building with HTML unescaping
7. ✅ Guild iteration and filtering
8. ✅ Settings retrieval per guild
9. ✅ Duplicate code detection
10. ✅ Channel resolution
11. ✅ Role notification formatting
12. ✅ Embed field generation
13. ✅ Message broadcasting
14. ✅ Reaction management
15. ✅ Database persistence
16. ✅ Error handling and logging

### Complexity Metrics

- **Lines of Code:** ~140 lines
- **Cyclomatic Complexity:** High (multiple nested conditionals)
- **Dependencies:** 5+ external services (bot, discord_helper, tracking_db, shift_codes_db, messaging)
- **Testability:** Difficult to test in isolation

---

## Recommended Refactorings

### Priority 1: Critical Extractions (High Impact)

#### 1. Extract Request Validation

**Current:** Inline validation scattered throughout method

**Proposed Method:**

```python
def _validate_shift_code_request(self, request: HttpRequest, headers: HttpHeaders) -> dict:
    """Validate and parse shift code request.
    
    Returns:
        Parsed payload dict
        
    Raises:
        HttpResponseException: If validation fails
    """
    if not request.body:
        err = ErrorStatusCodePayload({"code": 400, "error": "No payload found in the request"})
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())
    
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError as e:
        err = ErrorStatusCodePayload({
            "code": 400,
            "error": f"Invalid JSON payload: {str(e)}",
            "stacktrace": traceback.format_exc(),
        })
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())
    
    games = payload.get("games", [])
    if not games or len(games) == 0:
        err = ErrorStatusCodePayload({"code": 400, "error": "No games found in the payload"})
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())
    
    code = payload.get("code", None)
    if not code:
        err = ErrorStatusCodePayload({"code": 400, "error": "No code found in the payload"})
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())
    
    return payload
```

**Benefits:**

- Single responsibility: request validation
- Easy to unit test with various invalid payloads
- Consistent error response format
- Can add schema validation in future

**Testing:**

- Test missing body
- Test invalid JSON
- Test missing/empty games
- Test missing code
- Test valid payload

---

#### 2. Extract Code Normalization

**Current:** Inline string manipulation

**Proposed Method:**

```python
def _normalize_shift_code(self, code: str) -> str:
    """Normalize shift code format.
    
    Args:
        code: Raw shift code string
        
    Returns:
        Normalized code (uppercase, no spaces)
    """
    return str(code).strip().upper().replace(" ", "")
```

**Benefits:**

- Testable normalization logic
- Easy to add additional formatting rules
- Self-documenting
- Single source of truth for code format

**Testing:**

- Test lowercase conversion
- Test space removal
- Test whitespace stripping
- Test special character handling

---

#### 3. Extract Expiry Validation

**Current:** Inline expiry checking with seconds calculation

**Proposed Method:**

```python
def _check_code_expiry(self, expiry: Optional[int], headers: HttpHeaders) -> bool:
    """Check if code has expired.
    
    Args:
        expiry: Unix timestamp or None
        headers: HTTP headers for error response
        
    Returns:
        True if valid (not expired or no expiry), False otherwise
        
    Raises:
        HttpResponseException: If code is expired (202 status)
    """
    if not expiry:
        return True
    
    seconds_remaining = utils.get_seconds_until(expiry)
    if seconds_remaining <= 0:
        err = ErrorStatusCodePayload({"code": 202, "error": "Code is expired"})
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())
    
    return True
```

**Benefits:**

- Isolated expiry logic
- Easy to mock time for testing
- Clear return value semantics
- Consistent with other validation methods

**Testing:**

- Test expired timestamp (past)
- Test valid timestamp (future)
- Test no expiry (None)
- Test edge case (expires now)

---

#### 4. Extract Description Building

**Current:** Inline string concatenation with HTML unescaping

**Proposed Method:**

```python
def _build_shift_code_description(
    self, 
    code: str, 
    reward: str, 
    notes: Optional[str]
) -> str:
    """Build embed description for shift code.
    
    Args:
        code: Normalized shift code
        reward: Reward description
        notes: Optional notes
        
    Returns:
        Formatted description string
    """
    desc = f"**SHiFT Code:** `{code}`"
    desc += f"\n\n**{html.unescape(reward)}**"
    
    if notes:
        desc += f"\n\n*{html.unescape(notes)}*"
    
    desc += "\n\n**React:**\n✅ Working\n❌ Not Working"
    
    return desc
```

**Benefits:**

- Testable string formatting
- HTML unescape isolated
- Easy to modify template
- Clear input/output contract

**Testing:**

- Test with all fields
- Test with missing notes
- Test HTML entity unescaping
- Test special characters

---

#### 5. Extract Timestamp Message Formatting

**Current:** Inline timestamp formatting

**Proposed Method:**

```python
def _format_timestamp_messages(
    self, 
    expiry: Optional[int], 
    created_at: Optional[int]
) -> tuple[str, str]:
    """Format expiry and created timestamp messages.
    
    Args:
        expiry: Unix timestamp or None
        created_at: Unix timestamp or None
        
    Returns:
        Tuple of (expiry_message, created_message)
    """
    if expiry:
        expiry_msg = f"\nExpires: <t:{expiry}:R>"
    else:
        expiry_msg = "\nExpiry: `Unknown`"
    
    if created_at and isinstance(created_at, (int, float)):
        created_at = int(created_at)
        created_msg = f"\nPosted <t:{created_at}:R>"
    else:
        created_msg = ""
    
    return expiry_msg, created_msg
```

**Benefits:**

- Isolated timestamp formatting
- Easy to test different timestamp combinations
- Type validation centralized
- Discord timestamp format documented

**Testing:**

- Test with both timestamps
- Test with only expiry
- Test with only created_at
- Test with neither
- Test created_at type validation

---

### Priority 2: High-Value Extractions

#### 6. Extract Guild Processing Logic

**Current:** Large loop with multiple nested conditions

**Proposed Method:**

```python
async def _process_guild_broadcast(
    self,
    guild,
    code: str,
    payload: dict,
    embed_data: dict
) -> None:
    """Process shift code broadcast for a single guild.
    
    Args:
        guild: Discord guild object
        code: Normalized shift code
        payload: Original webhook payload
        embed_data: Pre-built embed data (description, fields, etc.)
    """
    guild_id = guild.id
    sc_settings = self.get_settings(guild_id, self.SETTINGS_SECTION)
    
    # Check if feature enabled
    if not sc_settings.get("enabled", False):
        self.log.debug(
            0, f"{self._module}.{self._class}.{inspect.stack()[0][3]}", 
            f"Shift Codes is disabled for guild {guild_id}"
        )
        return
    
    # Check if code already tracked
    if self.shift_codes_db.is_code_tracked(guild_id, code):
        self.log.debug(
            0, f"{self._module}.{self._class}.{inspect.stack()[0][3]}",
            f"Code `{code}` for guild '{guild_id}' is already being tracked"
        )
        return
    
    # Get and validate channels
    channels = await self._resolve_guild_channels(guild_id, sc_settings)
    if not channels:
        return
    
    # Build notification message
    notify_message = self._build_notify_message(sc_settings.get("notify_role_ids", []))
    
    # Broadcast to all channels
    await self._broadcast_to_channels(
        channels, guild_id, code, embed_data, notify_message, payload
    )
```

**Benefits:**

- Guild processing isolated
- Easier to test single guild scenarios
- Clearer separation of concerns
- Can parallelize guild processing in future

**Testing:**

- Test guild with feature disabled
- Test guild with code already tracked
- Test guild with no channels
- Test successful broadcast

---

#### 7. Extract Channel Resolution

**Current:** Inline channel fetching and validation

**Proposed Method:**

```python
async def _resolve_guild_channels(
    self, 
    guild_id: int, 
    settings: dict
) -> list:
    """Resolve Discord channels for shift code broadcast.
    
    Args:
        guild_id: Discord guild ID
        settings: Guild shift code settings
        
    Returns:
        List of valid channel objects
    """
    channel_ids = settings.get("channel_ids", [])
    if not channel_ids or len(channel_ids) == 0:
        self.log.debug(
            0, f"{self._module}.{self._class}.{inspect.stack()[0][3]}",
            f"No channel ids found for guild {guild_id}"
        )
        return []
    
    channels = []
    for channel_id in channel_ids:
        channel = await self.discord_helper.get_or_fetch_channel(int(channel_id))
        if channel:
            channels.append(channel)
    
    if len(channels) == 0:
        self.log.debug(
            0, f"{self._module}.{self._class}.{inspect.stack()[0][3]}",
            f"No channels found for guild {guild_id}"
        )
    
    return channels
```

**Benefits:**

- Channel resolution isolated
- Easy to mock for testing
- Clear input/output contract
- Can add channel validation logic

**Testing:**

- Test with no channel_ids
- Test with invalid channel_ids
- Test with valid channel_ids
- Test mixed valid/invalid channels

---

#### 8. Extract Role Notification Formatting

**Current:** Inline role mention string building

**Proposed Method:**

```python
def _build_notify_message(self, notify_role_ids: list) -> str:
    """Build role notification message.
    
    Args:
        notify_role_ids: List of role IDs to mention
        
    Returns:
        Formatted notification string with role mentions
    """
    if not notify_role_ids or len(notify_role_ids) == 0:
        return ""
    
    return " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])
```

**Benefits:**

- Simple, testable formatting
- Easy to modify mention format
- Clear responsibility
- Can add role validation

**Testing:**

- Test with empty list
- Test with single role
- Test with multiple roles
- Test with None

---

#### 9. Extract Embed Field Generation

**Current:** Inline loop creating fields

**Proposed Method:**

```python
def _build_embed_fields(self, games: list, code: str) -> list[dict]:
    """Build embed fields from games list.
    
    Args:
        games: List of game dicts with 'name' key
        code: Normalized shift code
        
    Returns:
        List of embed field dicts
    """
    fields = []
    for game in games:
        game_name = game.get("name", None)
        if not game_name:
            continue
        fields.append({
            "name": game_name,
            "value": f"**{code}**",
            "inline": False
        })
    return fields
```

**Benefits:**

- Testable field generation
- Easy to modify field format
- Handles missing game names
- Clear data structure

**Testing:**

- Test with multiple games
- Test with game missing name
- Test with empty games list
- Test field structure

---

#### 10. Extract Message Broadcasting

**Current:** Inline message send and reaction logic

**Proposed Method:**

```python
async def _broadcast_to_channels(
    self,
    channels: list,
    guild_id: int,
    code: str,
    embed_data: dict,
    notify_message: str,
    payload: dict
) -> None:
    """Broadcast shift code message to channels.
    
    Args:
        channels: List of channel objects
        guild_id: Discord guild ID
        code: Normalized shift code
        embed_data: Embed configuration dict
        notify_message: Role mention string
        payload: Original webhook payload
    """
    for channel in channels:
        message = await self.messaging.send_embed(
            channel=channel,
            title="SHiFT CODE ↗️",
            message=embed_data["message"],
            url=self.REDEEM_URL,
            image=None,
            delete_after=None,
            fields=embed_data["fields"],
            content=notify_message,
            view=embed_data["view"],
        )
        
        if message:
            await self._add_validation_reactions(message)
            self.shift_codes_db.add_shift_code(
                payload,
                {"guildId": guild_id, "channelId": channel.id, "messageId": message.id}
            )
```

**Benefits:**

- Broadcasting logic isolated
- Easy to test without Discord API
- Can add retry logic
- Clear responsibility

**Testing:**

- Test successful broadcast
- Test message is None
- Test reaction failures
- Test database persistence

---

#### 11. Extract Reaction Management

**Current:** Inline reaction adding

**Proposed Method:**

```python
async def _add_validation_reactions(self, message) -> None:
    """Add validation reactions to shift code message.
    
    Args:
        message: Discord message object
    """
    await message.add_reaction("✅")
    await message.add_reaction("❌")
```

**Benefits:**

- Simple, focused method
- Easy to modify reactions
- Can add error handling
- Testable independently

**Testing:**

- Test both reactions added
- Test reaction failure handling
- Test None message

---

### Priority 3: Code Quality Improvements

#### 12. Add Type Hints

**Current:** Some type hints missing

**Improvement:** Add complete type hints to all methods

```python
from typing import Optional, List, Dict, Tuple

async def shift_code(self, request: HttpRequest) -> HttpResponse:
    ...

def _normalize_shift_code(self, code: str) -> str:
    ...

def _build_embed_fields(self, games: List[Dict[str, str]], code: str) -> List[Dict[str, str]]:
    ...
```

---

#### 13. Centralize Error Response Creation

**Current:** Inline error response creation

**Proposed:** Add helper method (similar to MinecraftPlayerWebhookHandler)

```python
def _create_error_response(
    self,
    status_code: int,
    error_message: str,
    headers: HttpHeaders,
    include_stacktrace: bool = False
) -> HttpResponse:
    """Create standardized error response."""
    err_data = {
        "code": status_code,
        "error": error_message,
    }
    if include_stacktrace:
        err_data["stacktrace"] = traceback.format_exc()
    
    err = ErrorStatusCodePayload(err_data)
    return HttpResponse(
        status_code,
        headers,
        json.dumps(err.to_dict()).encode("utf-8")
    )
```

---

## Refactored Method Structure

### Before (Current)

```python
async def shift_code(self, request: HttpRequest) -> HttpResponse:
    # ~140 lines of mixed validation, processing, and broadcasting
    ...
```

### After (Proposed)

```python
async def shift_code(self, request: HttpRequest) -> HttpResponse:
    """Main entry point - orchestrates the workflow."""
    _method = inspect.stack()[0][3]
    
    try:
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        
        # 1. Authentication
        if not self.validate_webhook_token(request):
            return self._create_error_response(401, "Invalid webhook token", headers)
        
        # 2. Validate and parse request
        payload = self._validate_shift_code_request(request, headers)
        
        # 3. Extract and normalize data
        code = self._normalize_shift_code(payload["code"])
        
        # 4. Check expiry
        self._check_code_expiry(payload.get("expiry"), headers)
        
        # 5. Build embed data
        description = self._build_shift_code_description(
            code,
            payload.get("reward", "Unknown"),
            payload.get("notes")
        )
        expiry_msg, created_msg = self._format_timestamp_messages(
            payload.get("expiry"),
            payload.get("created_at")
        )
        fields = self._build_embed_fields(payload["games"], code)
        
        # 6. Build view
        buttons = MultipleExternalUrlButtonView([
            ButtonData("Redeem", self.REDEEM_URL),
            ButtonData("Open Source", payload.get("source"))
        ])
        
        embed_data = {
            "message": f"{expiry_msg}{created_msg}\n\n{description}",
            "fields": fields,
            "view": buttons
        }
        
        # 7. Process each guild
        for guild in self.bot.guilds:
            await self._process_guild_broadcast(guild, code, payload, embed_data)
        
        # 8. Return success
        return HttpResponse(200, headers, json.dumps(payload, indent=4).encode())
        
    except HttpResponseException as e:
        return HttpResponse(e.status_code, e.headers, e.body)
    except Exception as e:
        self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
        if 'headers' not in locals():
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")
        return self._create_error_response(500, f"Internal server error: {str(e)}", headers, True)
```

---

## Testing Impact

### Before Refactoring

**Test Complexity:**

- Need to mock: bot, discord_helper, tracking_db, shift_codes_db, messaging, utils
- Need to set up: guilds, channels, messages, settings
- Hard to test individual validation steps
- Difficult to test error paths

**Example Test Setup:**

```python
# 50+ lines of mock setup required for each test
```

### After Refactoring

**Test Complexity:**

- Unit tests for each helper (minimal mocking)
- Integration tests for main flow
- Focused tests for each concern

**Example Test Setup:**

```python
def test_normalize_shift_code():
    handler = ShiftCodeWebhookHandler(mock_bot)
    assert handler._normalize_shift_code("abcd 1234") == "ABCD1234"
```

---

## Implementation Priority

### Phase 1: Critical Foundations (~2 hours)

1. ✅ Add `_create_error_response` helper
1. ✅ Extract `_validate_shift_code_request`
1. ✅ Extract `_normalize_shift_code`
1. ✅ Extract `_check_code_expiry`

### Phase 2: Description Building (~1 hour)

1. ✅ Extract `_build_shift_code_description`
1. ✅ Extract `_format_timestamp_messages`
1. ✅ Extract `_build_embed_fields`

### Phase 3: Guild Processing (~2 hours)

1. ✅ Extract `_resolve_guild_channels`
1. ✅ Extract `_build_notify_message`
1. ✅ Extract `_process_guild_broadcast`
1. ✅ Extract `_broadcast_to_channels`
1. ✅ Extract `_add_validation_reactions`

### Phase 4: Polish (~1 hour)

1. ✅ Add complete type hints
1. ✅ Update docstrings
1. ✅ Add tests for all helpers

**Total Estimated Time:** ~6 hours

---

## Benefits Summary

### Testability ⭐⭐⭐⭐⭐

- Unit tests for each helper
- Isolated validation logic
- Easy to mock dependencies
- Clear test scenarios

### Maintainability ⭐⭐⭐⭐⭐

- Single responsibility per method
- Easy to locate and fix bugs
- Clear separation of concerns
- Self-documenting code

### Extensibility ⭐⭐⭐⭐⭐

- Easy to add new validations
- Can modify formatting independently
- Can add caching/rate limiting
- Template for other webhooks

### Code Quality ⭐⭐⭐⭐⭐

- Reduced cyclomatic complexity
- Better error handling
- Consistent patterns
- Type safety

---

## Future Enhancements

### Performance Optimizations

- **Parallel Guild Processing**
  - Process guilds concurrently with asyncio.gather
  - Significant speedup for many guilds

- **Channel Caching**
  - Cache channel objects (short TTL)
  - Reduce Discord API calls

- **Duplicate Detection Optimization**
  - Batch check all guilds at once
  - Single database query

### Feature Additions

- **Code Validation**
  - Validate code format (regex)
  - Check for known invalid patterns

- **Rate Limiting**
  - Per-source rate limiting
  - Prevent webhook spam

- **Webhook Signatures**
  - Verify request authenticity
  - Prevent unauthorized posts

- **Analytics**
  - Track code usage/reactions
  - Popular games tracking
  - Expiry effectiveness

---

## Conclusion

The `ShiftCodeWebhookHandler.shift_code` method follows a similar pattern to the previously refactored `MinecraftPlayerWebhookHandler`. The proposed extractions will significantly improve testability while maintaining all existing functionality.

**Key Takeaways:**

- Extract validation logic into focused methods
- Separate formatting from business logic
- Isolate external dependencies
- Use consistent error handling patterns
- Add comprehensive tests for each helper

**Recommendation:** Implement refactoring in phases, starting with validation helpers (Phase 1). This provides immediate testability benefits while being low-risk.
