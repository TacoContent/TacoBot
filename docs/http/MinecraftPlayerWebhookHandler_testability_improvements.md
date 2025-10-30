# MinecraftPlayerWebhookHandler Testability & Quality Improvements

## Summary

Analysis of the `event()` method in `MinecraftPlayerWebhookHandler` revealed several opportunities for improved testability, error handling, and maintainability.

---

## 🐛 CRITICAL BUG FOUND

### Issue: Unhandled HttpResponseException in Final Exception Handler

**Location:** `bot/lib/http/handlers/webhook/MinecraftPlayerWebhookHandler.py:206`

**Problem:**

```python
except HttpResponseException as e:
    return HttpResponse(e.status_code, e.headers, e.body)
except Exception as e:
    self.log.error(...)
    err = ErrorStatusCodePayload(...)
    raise HttpResponseException(500, headers, bytearray(...))  # ← NOT CAUGHT!
```

The `HttpResponseException` raised in the final `except Exception` block is NOT caught by the `except HttpResponseException` handler because it's outside that try-except scope. This means 500 errors will propagate as exceptions instead of being returned as HTTP responses.

**Fix:**

```python
except HttpResponseException as e:
    return HttpResponse(e.status_code, e.headers, e.body)
except Exception as e:
    self.log.error(...)
    err = ErrorStatusCodePayload(...)
    # Return HttpResponse directly instead of raising
    return HttpResponse(500, headers, bytearray(json.dumps(err.to_dict()), "utf-8"))
```

**Impact:** Medium-High

- Breaks HTTP contract (exceptions instead of responses)
- Makes testing difficult
- May crash request handling in production

---

## 🎯 Testability Improvements

### 1. Extract Validation Logic into Separate Methods

**Current Problem:** All validation is inline in the `event()` method, making it harder to test validation logic in isolation.

**Suggestion:**

```python
def _validate_request_body(self, request: HttpRequest, headers: HttpHeaders) -> dict:
    """Validate and parse request body.

    Returns:
        Parsed JSON payload dict

    Raises:
        HttpResponseException: If validation fails
    """
    if not request.body:
        err = ErrorStatusCodePayload({"code": 400, "error": "No payload found in the request"})
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

    try:
        return json.loads(request.body)
    except json.JSONDecodeError as e:
        err = ErrorStatusCodePayload({
            "code": 400,
            "error": f"Invalid JSON payload: {str(e)}",
            "stacktrace": traceback.format_exc(),
        })
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

def _validate_payload_fields(self, payload: dict, headers: HttpHeaders) -> tuple[int, str, dict]:
    """Validate required fields in payload.

    Returns:
        Tuple of (guild_id, event_str, data_payload)

    Raises:
        HttpResponseException: If required fields are missing
    """
    if not payload.get("guild_id", None):
        raise HttpResponseException(404, headers, b'{ "error": "No guild_id found in the payload" }')
    if not payload.get("event", None):
        raise HttpResponseException(404, headers, b'{ "error": "No event found in the payload" }')
    if not payload.get("payload", None):
        raise HttpResponseException(404, headers, b'{ "error": "No payload object found in the payload" }')

    guild_id = int(payload.get("guild_id", 0))
    data_payload = payload.get("payload", {})
    event_str = payload.get("event", "")

    return guild_id, event_str, data_payload

def _validate_event_type(self, event_str: str, headers: HttpHeaders) -> MinecraftPlayerEvents:
    """Validate and parse event type.

    Returns:
        MinecraftPlayerEvents enum value

    Raises:
        HttpResponseException: If event type is unknown
    """
    event = MinecraftPlayerEvents.from_str(event_str)
    if event == MinecraftPlayerEvents.UNKNOWN:
        err = ErrorStatusCodePayload({"code": 404, "error": f"Unknown event type: {event_str}"})
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())
    return event
```

**Benefits:**

- Each validation method can be tested independently
- Clearer separation of concerns
- Easier to add new validation rules
- Better error messages (can include the invalid value)

---

### 2. Extract Discord Object Resolution Logic

**Current Problem:** Discord user/guild/member fetching is inline, making it hard to test without mocking multiple Discord API calls.

**Suggestion:**

```python
async def _resolve_discord_objects(
    self,
    guild_id: int,
    user_id: int,
    headers: HttpHeaders
) -> tuple:
    """Resolve Discord user, guild, and member objects.

    Returns:
        Tuple of (discord_user, guild, member)

    Raises:
        HttpResponseException: If any object cannot be found
    """
    # Get discord user from user_id
    discord_user = await self.discord_helper.get_or_fetch_user(user_id)
    if not discord_user:
        err = ErrorStatusCodePayload({"code": 404, "error": f"User {user_id} not found"})
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

    # Get the guild from the guild_id
    guild = await self.bot.fetch_guild(guild_id)
    if not guild:
        err = ErrorStatusCodePayload({"code": 404, "error": f"Guild {guild_id} not found"})
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

    # Get the member from the user_id
    member = await guild.fetch_member(user_id)
    if not member:
        err = ErrorStatusCodePayload({
            "code": 404,
            "error": f"Member {user_id} not found in guild {guild_id}"
        })
        raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

    return discord_user, guild, member
```

**Benefits:**

- Single method to mock for Discord resolution testing
- Clearer error messages with actual IDs
- Easier to add caching layer later
- Can be reused by other webhook handlers

---

### 3. Standardize Error Response Creation

**Current Problem:** Error responses are created inline with inconsistent formats (some use ErrorStatusCodePayload, some use raw JSON strings).

**Suggestion:**

```python
def _create_error_response(
    self,
    status_code: int,
    error_message: str,
    headers: HttpHeaders,
    include_stacktrace: bool = False
) -> HttpResponse:
    """Create standardized error response.

    Args:
        status_code: HTTP status code
        error_message: Human-readable error message
        headers: HTTP headers to include
        include_stacktrace: Whether to include exception stacktrace

    Returns:
        HttpResponse with ErrorStatusCodePayload body
    """
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

**Benefits:**

- Consistent error response format
- Centralized error logging
- Easier to change error format project-wide
- Type-safe (always uses ErrorStatusCodePayload)

---

### 4. Use Dependency Injection for Discord Helper

**Current Problem:** `discord_helper` is created in `__init__`, making it hard to mock without patching.

**Suggestion:**

```python
def __init__(self, bot, discord_helper: Optional[discordhelper.DiscordHelper] = None):
    super().__init__(bot)
    self._class = self.__class__.__name__
    self.SETTINGS_SECTION = "webhook/minecraft/player"
    # Allow injecting discord_helper for testing
    self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)
```

**Benefits:**

- Easier to inject mock in tests
- More testable without monkeypatching
- Follows dependency injection pattern

---

### 5. Add Request Context Logging

**Current Problem:** Debug logs don't include request correlation ID or timing information.

**Suggestion:**

```python
async def event(self, request: HttpRequest, **kwargs) -> HttpResponse:
    _method = inspect.stack()[0][3]
    request_id = str(uuid.uuid4())[:8]  # Short request ID
    start_time = time.time()

    try:
        self.log.debug(0, f"{self._module}.{self._class}.{_method}",
                      f"[{request_id}] Received webhook request")
        # ... rest of method ...
    finally:
        duration_ms = (time.time() - start_time) * 1000
        self.log.debug(0, f"{self._module}.{self._class}.{_method}",
                      f"[{request_id}] Request completed in {duration_ms:.2f}ms")
```

**Benefits:**

- Easier to correlate logs with requests
- Performance monitoring built-in
- Request-level tracing for debugging

---

### 6. Improve Event Routing Readability

**Current Problem:** Match statement returns directly from cases, making it less clear that this is the final routing logic.

**Suggestion:**

```python
# Route to appropriate event handler
event_handlers = {
    MinecraftPlayerEvents.LOGIN: self._handle_login_event,
    MinecraftPlayerEvents.LOGOUT: self._handle_logout_event,
    MinecraftPlayerEvents.DEATH: self._handle_death_event,
}

handler_func = event_handlers.get(event)
if handler_func is None:
    err = ErrorStatusCodePayload({"code": 404, "error": f"No handler for event: {event}"})
    raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())

return await handler_func(guild, member, discord_user, data_payload, headers)
```

**Benefits:**

- More Pythonic (dictionary dispatch)
- Easier to add new event types dynamically
- Clearer error when handler is missing
- Could be moved to class-level constant

---

### 7. Add Type Hints to All Parameters

**Current Problem:** Some parameters lack type hints, reducing IDE support and static analysis.

**Suggestion:**

```python
async def _handle_login_event(
    self,
    guild: discord.Guild,  # Type hint
    member: discord.Member,  # Type hint
    discord_user: discord.User,  # Type hint
    data_payload: dict[str, Any],  # Type hint
    headers: HttpHeaders
) -> HttpResponse:
```

**Benefits:**

- Better IDE autocomplete
- Static type checking with mypy
- Self-documenting code
- Catches type errors at development time

---

### 8. Add Validation for user_id in Payload

**Current Problem:** `user_id` is extracted from payload but never validated before use.

**Suggestion:**

```python
user_id = data_payload.get("user_id", 0)
if not user_id or not isinstance(user_id, int):
    err = ErrorStatusCodePayload({
        "code": 400,
        "error": "Missing or invalid user_id in payload"
    })
    raise HttpResponseException(err.code, headers, json.dumps(err.to_dict()).encode())
```

**Benefits:**

- Fail fast with clear error message
- Prevent passing 0 or None to Discord API
- Better error messages for clients

---

## 📊 Refactored Event Method (Recommended)

```python
async def event(self, request: HttpRequest, **kwargs) -> HttpResponse:
    """Ingress point for Minecraft player events.

    Expected JSON Body:
        guild_id (int)  : Target Discord guild id.
        event (str)     : One of the supported minecraft player events
                            (LOGIN, LOGOUT, DEATH, ...).
        payload (object): Event-specific data. Must contain at least
                            ``user_id`` used to resolve the Discord user.

    Returns:
        200 JSON with echo + normalized event meta on success.
        4xx JSON error for missing/invalid fields or unknown event.
        500 JSON error for unexpected processing failures.
    """
    _method = inspect.stack()[0][3]
    request_id = str(uuid.uuid4())[:8]

    try:
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        headers.add("X-TACOBOT-EVENT", "MinecraftPlayerEvent")
        headers.add("X-Request-ID", request_id)

        # Authentication
        if not self.validate_webhook_token(request):
            return self._create_error_response(
                401, "Invalid webhook token", headers
            )

        # Parse and validate request
        payload = self._validate_request_body(request, headers)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}",
                      f"[{request_id}] {json.dumps(payload, indent=2)}")

        # Validate payload structure
        guild_id, event_str, data_payload = self._validate_payload_fields(payload, headers)
        event = self._validate_event_type(event_str, headers)

        # Extract and validate user_id
        user_id = data_payload.get("user_id", 0)
        if not user_id:
            return self._create_error_response(
                400, "Missing user_id in payload", headers
            )

        # Resolve Discord objects
        discord_user, guild, member = await self._resolve_discord_objects(
            guild_id, user_id, headers
        )

        # Route to event handler
        event_handlers = {
            MinecraftPlayerEvents.LOGIN: self._handle_login_event,
            MinecraftPlayerEvents.LOGOUT: self._handle_logout_event,
            MinecraftPlayerEvents.DEATH: self._handle_death_event,
        }

        handler_func = event_handlers.get(event)
        if handler_func is None:
            return self._create_error_response(
                404, f"No handler for event: {event}", headers
            )

        return await handler_func(guild, member, discord_user, data_payload, headers)

    except HttpResponseException as e:
        return HttpResponse(e.status_code, e.headers, e.body)
    except Exception as e:
        self.log.error(0, f"{self._module}.{self._class}.{_method}",
                      f"[{request_id}] {str(e)}", traceback.format_exc())
        return self._create_error_response(
            500, f"Internal server error: {str(e)}", headers, include_stacktrace=True
        )
```

---

## 🧪 Testing Impact

With these changes, tests become much simpler:

### Before (Complex Mocking)

```python
async def test_event_success(handler, mock_request):
    handler.validate_webhook_token = MagicMock(return_value=True)
    handler.discord_helper = MagicMock()
    handler.discord_helper.get_or_fetch_user = AsyncMock(return_value=mock_user)
    handler.bot.fetch_guild = AsyncMock(return_value=mock_guild)
    mock_guild.fetch_member = AsyncMock(return_value=mock_member)
    # ... test logic
```

### After (Simple Mocking)

```python
async def test_event_success(handler, mock_request):
    handler._validate_request_body = MagicMock(return_value={"guild_id": 123, ...})
    handler._resolve_discord_objects = AsyncMock(return_value=(user, guild, member))
    # ... test logic - much clearer!
```

---

## ⚡ Performance Improvements

1. **Caching Discord Objects**: The `_resolve_discord_objects` method could easily add an LRU cache
2. **Async Logging**: Debug logging could be made non-blocking
3. **Early Returns**: Validation failures return immediately instead of continuing through the method

---

## 🔒 Security Improvements

1. **Rate Limiting**: Could be added to `_validate_request_body`
2. **Request Signing**: Could validate HMAC signatures in authentication
3. **Payload Size Limits**: Could enforce max payload size in `_validate_request_body`

---

## 📝 Documentation Improvements

1. All extracted methods have clear docstrings
2. Type hints make intent clear
3. Error messages include contextual information (IDs, event types)

---

## Implementation Priority

1. **CRITICAL** - Fix the HttpResponseException bug in except handler (5 min)
2. **HIGH** - Extract `_create_error_response` for consistency (15 min)
3. **HIGH** - Extract `_validate_request_body` for better JSON error handling (20 min)
4. **MEDIUM** - Extract `_resolve_discord_objects` for testability (20 min)
5. **MEDIUM** - Extract validation methods (30 min)
6. **LOW** - Add request correlation IDs (15 min)
7. **LOW** - Switch to dictionary dispatch for event routing (10 min)

**Total Estimated Time**: ~2 hours for all improvements

---

## Backwards Compatibility

All suggested changes are backwards compatible:

- Public API (`event()` signature) unchanged
- Response formats unchanged
- Error codes unchanged
- Only internal structure improved

---

## Testing Strategy

After refactoring:

1. Run existing tests to ensure no regressions
2. Add tests for new private methods
3. Add integration tests for full request flows
4. Add performance benchmarks

---

## Conclusion

These improvements will make the codebase:

- **More testable** - Easier to unit test individual pieces
- **More maintainable** - Clear separation of concerns
- **More reliable** - Fix critical exception handling bug
- **More debuggable** - Better logging and error messages
- **More extensible** - Easy to add new event types

The refactoring can be done incrementally without breaking existing functionality.
