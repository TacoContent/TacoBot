# PromptHelper

Helper class for user interaction prompts and input collection. It centralizes yes/no confirmations, channel selection, role selection, numeric and text inputs, and image-or-text capture. This mirrors and replaces the prompt-related methods formerly on DiscordHelper.

- Module: `bot.lib.helpers.prompt_helper`
- Class: `PromptHelper`
- Requires: a running Discord bot instance and the Messaging/Settings infrastructure

## Responsibilities

- Ask users for input via embeds and Discord UI components
- Handle timeouts and deliver clear feedback
- Ensure correct scoping: DM vs guild channel behavior
- Clean up prompt and response messages when appropriate

## Dependencies

- `bot.lib.messaging.Messaging` for sending embeds
- `bot.lib.settings.Settings` for text and i18n strings
- `bot.lib.YesOrNoView.YesOrNoView` for yes/no button prompts
- `bot.lib.ChannelSelect.ChannelSelectView` for channel selection
- `bot.lib.RoleSelectView.RoleSelectView` for role selection
- `bot.lib.models.textwithattachments.TextWithAttachments` for image/text responses

Note on Messaging API: `Messaging.send_embed` is typically called as:

```python
await messaging.send_embed(channel, title, message, **kwargs)
```

The first three parameters are positional: `channel`, `title`, then `message`.

## Constructor

```python
PromptHelper(bot)
```

- `bot`: Discord bot (commands.Bot or similar) used for `wait_for` and context

## Methods

### ask_yes_no

```python
await ask_yes_no(
    ctx,
    targetChannel,
    question: str,
    title: str = "Yes or No?",
    timeout: int = 60,
    fields: list[dict] | None = None,
    thumbnail: str | None = None,
    image: str | None = None,
    content: str | None = None,
    result_callback: Callable[[bool], Awaitable[None]] | None = None,
) -> None
```

- Shows an embed with a Yes/No button view.
- Calls `result_callback(True|False)` when answered or times out (False on timeout).
- Message auto-deletes after `timeout` seconds.

### ask_channel_by_name_or_id

```python
channel = await ask_channel_by_name_or_id(
    ctx,
    title: str = "TacoBot",
    description: str = "Enter the name of the channel",
    timeout: int = 60,
)
```

- Prompts user to type a channel name or ID.
- Returns the resolved channel or `None` on timeout or if not found.
- Cleans up the user’s response and the prompt message when possible.

### ask_channel

```python
await ask_channel(
    ctx,
    title: str = "Choose Channel",
    message: str = "Please choose a channel.",
    allow_none: bool = False,
    timeout: int = 60,
    callback: Callable[[discord.abc.GuildChannel | None], Awaitable[None]] | None = None,
)
```

- Presents a dropdown of text channels (sorted by position) using ChannelSelectView.
- If the user selects “manual entry”, it falls back to `ask_channel_by_name_or_id`.
- Invokes `callback(selected_channel or None)`.

### ask_number

```python
value = await ask_number(
    ctx,
    title: str = "Enter Number",
    message: str = "Please enter a number.",
    min_value: int = 0,
    max_value: int = 100,
    timeout: int = 60,
) -> int | None
```

- Waits for a numeric reply from the invoking user.
- Enforces inclusive range `[min_value, max_value]`.
- Returns `int` value or `None` on timeout.
- Cleans up prompt and reply where permissions allow.

### ask_text

```python
text = await ask_text(
    ctx,
    targetChannel,
    title: str = "Enter Text Response",
    message: str = "Please enter your response.",
    timeout: int = 60,
    color: int | None = None,
) -> str | None
```

- Collects a text response from the invoking user.
- In DMs: does not delete the user’s message; in guilds: deletes the reply when possible.
- Returns the response text or `None` on timeout.

### ask_for_image_or_text

```python
payload = await ask_for_image_or_text(
    ctx,
    targetChannel,
    title: str = "Enter Text Response",
    message: str = "Please enter your response.",
    timeout: int = 60,
    color: int | None = None,
) -> TextWithAttachments | None
```

- Returns a `TextWithAttachments(text, attachments)` combining the user’s message and any attachments.
- DM/guild cleanup behavior matches `ask_text`.
- Returns `None` on timeout.

### ask_role_list

```python
await ask_role_list(
    ctx,
    title: str = "Choose Role",
    message: str = "Please choose a role.",
    allow_none: bool = False,
    exclude_roles: list[str] | None = None,
    timeout: int = 60,
    select_callback: Callable[[discord.Role | None], Awaitable[None]] | None = None,
) -> discord.Role | None
```

- Displays RoleSelectView for selecting a role.
- Calls `select_callback(role or None)` with the selected role (or `None` for cancel/manual path).
- Sends a timeout message if no selection is made in time.

## Usage Example

```python
from bot.lib.helpers import PromptHelper

class MyCog:
    def __init__(self, bot):
        self.bot = bot
        self.prompts = PromptHelper(bot)

    async def configure_channel(self, ctx):
        async def on_selected(channel):
            if channel:
                await ctx.send(f"Selected: {channel.mention}")
            else:
                await ctx.send("No channel selected")

        await self.prompts.ask_channel(
            ctx,
            title="Choose Channel",
            message="Pick a channel for announcements",
            allow_none=True,
            timeout=60,
            callback=on_selected,
        )
```

## Testing Guidance

- Mock `bot.wait_for` with `AsyncMock` and control the returned `message` object.
- Replace `PromptHelper.messaging.send_embed` with an `AsyncMock` to assert calls and kwargs.
- Remember: `send_embed(channel, title, message, **kwargs)` → title and message are positional in our helpers.
- DM vs Guild:
  - In DMs, user messages are NOT deleted.
  - In guild channels, helper attempts to delete prompt and user reply where permitted.
- Timeouts: Expect a follow-up timeout message (`took_too_long`) and a `None` or callback invocation with a non-success value.

## Error Handling & Edge Cases

- All methods guard against timeouts with user-friendly feedback.
- Channel/role lookups gracefully handle unknown selections.
- Cleanup (deleting messages) is wrapped to ignore NotFound/Forbidden.
- ask_for_image_or_text ensures responses originate from the right channel or the same DM thread.

## Notes

- Strings such as `footer_XX_seconds`, `took_too_long`, and message templates rely on `Settings.get_string` and your language packs.
- Keep prompts short and clear; prefer embeds over plain text for consistency.
