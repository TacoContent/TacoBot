"""Tests for MessagePreview cog (message_preview.py).
Covers Discord message link detection, preview creation, and embed handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.message_preview import MessagePreview


@pytest.fixture
def cog(bot, entity_helper, messaging, tracking_db, settings):
    """Create a MessagePreview cog instance with all mocked dependencies."""
    with patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"):
        cog_instance = MessagePreview(
            bot=bot, entity_helper=entity_helper, messaging=messaging, tracking_db=tracking_db, settings=settings
        )
        return cog_instance


class DummyGuild:
    def __init__(self, id):
        self.id = id


class DummyChannel:
    def __init__(self, id, guild_id=None):
        self.id = id
        self.guild_id = guild_id
        self.fetch_message = AsyncMock()


class DummyUser:
    def __init__(self, id, bot=False, name="TestUser"):
        self.id = id
        self.bot = bot
        self.name = name
        self.display_name = name
        self.discriminator = "0"
        self.global_name = name


class DummyMessage:
    def __init__(self, id, guild, channel, author, content="", embeds=None, attachments=None, created_at=None):
        self.id = id
        self.guild = guild
        self.channel = channel
        self.author = author
        self.content = content
        self.embeds = embeds or []
        self.attachments = attachments or []
        if guild and channel:
            self.jump_url = f"https://discord.com/channels/{guild.id}/{channel.id}/{id}"
        else:
            self.jump_url = f"https://discord.com/channels/0/0/{id}"
        self.created_at = created_at or MagicMock()
        self.created_at.strftime = MagicMock(return_value="2025-01-01 12:00:00")
        self.delete = AsyncMock()


class DummyEmbed:
    def __init__(self, title="", description="", color=None, thumbnail=None, image=None, fields=None):
        self.title = title
        self.description = description
        self.color = color
        self.thumbnail = MagicMock() if thumbnail else None
        if self.thumbnail:
            self.thumbnail.url = thumbnail
        self.image = MagicMock() if image else None
        if self.image:
            self.image.url = image
        self.fields = fields or []


class DummyEmbedField:
    def __init__(self, name, value, inline=False):
        self.name = name
        self.value = value
        self.inline = inline


class DummyAttachment:
    def __init__(self, url):
        self.url = url


@pytest.mark.asyncio
class TestMessagePreviewOnMessage:
    """Tests for on_message event handler."""

    async def test_on_message_dm_ignored(self, cog):
        """Test that DM messages are ignored."""
        message = DummyMessage(
            123,
            None,  # No guild (DM)
            DummyChannel(456),
            DummyUser(789),
            content="https://discord.com/channels/100/200/300",
        )

        await cog.on_message(message)

        # Should not process DM messages
        cog.entity_helper.get_or_fetch_channel.assert_not_called()
        cog.tracking_db.track_command_usage.assert_not_called()

    async def test_on_message_bot_ignored(self, cog):
        """Test that bot messages are ignored."""
        guild = DummyGuild(100)
        channel = DummyChannel(200)
        bot_user = DummyUser(300, bot=True)
        message = DummyMessage(400, guild, channel, bot_user, content="https://discord.com/channels/100/200/300")

        await cog.on_message(message)

        # Should not process bot messages
        cog.entity_helper.get_or_fetch_channel.assert_not_called()
        cog.tracking_db.track_command_usage.assert_not_called()

    async def test_on_message_no_link(self, cog):
        """Test that messages without Discord links are ignored."""
        guild = DummyGuild(100)
        channel = DummyChannel(200)
        user = DummyUser(300)
        message = DummyMessage(400, guild, channel, user, content="Just a normal message")

        await cog.on_message(message)

        # Should not process messages without links
        cog.entity_helper.get_or_fetch_channel.assert_not_called()

    async def test_on_message_valid_discord_link(self, cog):
        """Test processing a valid Discord message link."""
        guild_id = 100
        channel_id = 200
        message_id = 300
        guild = DummyGuild(guild_id)
        source_channel = DummyChannel(400)
        user = DummyUser(500)
        source_message = DummyMessage(
            600,
            guild,
            source_channel,
            user,
            content=f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}",
        )

        # Mock the target channel and message
        target_channel = DummyChannel(channel_id)
        target_message = DummyMessage(message_id, guild, target_channel, user, content="Referenced message")
        target_channel.fetch_message = AsyncMock(return_value=target_message)

        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=target_channel)
        cog.messaging.send_embed = AsyncMock(return_value=MagicMock())

        await cog.on_message(source_message)

        # Verify channel was fetched
        cog.entity_helper.get_or_fetch_channel.assert_awaited_once_with(channel_id)

        # Verify message was fetched
        target_channel.fetch_message.assert_awaited_once_with(message_id)

        # Verify preview was created
        cog.messaging.send_embed.assert_awaited_once()

        # Verify original message was deleted
        source_message.delete.assert_awaited_once()

        # Verify command usage was tracked
        cog.tracking_db.track_command_usage.assert_called_once()

    async def test_on_message_discordapp_link(self, cog):
        """Test processing a discordapp.com link (old format)."""
        guild_id = 100
        channel_id = 200
        message_id = 300
        guild = DummyGuild(guild_id)
        source_channel = DummyChannel(400)
        user = DummyUser(500)
        source_message = DummyMessage(
            600,
            guild,
            source_channel,
            user,
            content=f"https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id}",
        )

        target_channel = DummyChannel(channel_id)
        target_message = DummyMessage(message_id, guild, target_channel, user, content="Referenced message")
        target_channel.fetch_message = AsyncMock(return_value=target_message)

        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=target_channel)
        cog.messaging.send_embed = AsyncMock(return_value=MagicMock())

        await cog.on_message(source_message)

        # Should process discordapp.com links
        cog.entity_helper.get_or_fetch_channel.assert_awaited_once()
        cog.messaging.send_embed.assert_awaited_once()

    async def test_on_message_different_guild(self, cog):
        """Test that links to different guilds are ignored."""
        guild_id = 100
        other_guild_id = 999
        channel_id = 200
        message_id = 300
        guild = DummyGuild(guild_id)
        channel = DummyChannel(400)
        user = DummyUser(500)
        message = DummyMessage(
            600,
            guild,
            channel,
            user,
            content=f"https://discord.com/channels/{other_guild_id}/{channel_id}/{message_id}",
        )

        target_channel = DummyChannel(channel_id)
        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=target_channel)

        await cog.on_message(message)

        # Should not create preview for different guild
        cog.messaging.send_embed.assert_not_called()
        message.delete.assert_not_called()

    async def test_on_message_channel_not_found(self, cog):
        """Test handling when referenced channel is not found."""
        guild_id = 100
        channel_id = 200
        message_id = 300
        guild = DummyGuild(guild_id)
        channel = DummyChannel(400)
        user = DummyUser(500)
        message = DummyMessage(
            600, guild, channel, user, content=f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        )

        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)

        await cog.on_message(message)

        # Should handle gracefully when channel not found
        cog.messaging.send_embed.assert_not_called()
        message.delete.assert_not_called()
        cog.log.debug.assert_called()

    async def test_on_message_message_not_found(self, cog):
        """Test handling when referenced message is not found."""
        guild_id = 100
        channel_id = 200
        message_id = 300
        guild = DummyGuild(guild_id)
        source_channel = DummyChannel(400)
        user = DummyUser(500)
        source_message = DummyMessage(
            600,
            guild,
            source_channel,
            user,
            content=f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}",
        )

        target_channel = DummyChannel(channel_id)
        target_channel.fetch_message = AsyncMock(return_value=None)

        cog.entity_helper.get_or_fetch_channel = AsyncMock(return_value=target_channel)

        await cog.on_message(source_message)

        # Should handle gracefully when message not found
        cog.messaging.send_embed.assert_not_called()
        source_message.delete.assert_not_called()
        cog.log.debug.assert_called()

    async def test_on_message_exception_handling(self, cog):
        """Test exception handling in on_message."""
        guild = DummyGuild(100)
        channel = DummyChannel(200)
        user = DummyUser(300)
        message = DummyMessage(400, guild, channel, user, content="https://discord.com/channels/100/200/300")

        cog.entity_helper.get_or_fetch_channel = AsyncMock(side_effect=Exception("Test error"))

        # Should not raise exception
        await cog.on_message(message)

        # Verify error was logged
        cog.log.error.assert_called()


@pytest.mark.asyncio
class TestMessagePreviewCreatePreview:
    """Tests for create_message_preview method."""

    async def test_create_message_preview_simple_message(self, cog):
        """Test creating preview for a simple text message."""
        guild = DummyGuild(100)
        source_channel = DummyChannel(200)
        target_channel = DummyChannel(300)
        user = DummyUser(400)

        ctx = DummyMessage(500, guild, source_channel, user)
        ref_message = DummyMessage(600, guild, target_channel, user, content="Hello world!")

        mock_embed = MagicMock()
        cog.messaging.send_embed = AsyncMock(return_value=mock_embed)

        result = await cog.create_message_preview(ctx, ref_message)

        # Verify embed was created
        cog.messaging.send_embed.assert_awaited_once()
        call_args = cog.messaging.send_embed.call_args

        # Verify channel
        assert call_args[0][0] == source_channel

        # Verify content includes message content
        message_arg = call_args[1]["message"]
        assert "Hello world!" in message_arg

        # Verify author
        assert call_args[1]["author"] == user

        # Verify URL
        assert call_args[1]["url"] == ref_message.jump_url

        # Verify result
        assert result == mock_embed

    async def test_create_message_preview_with_embed(self, cog):
        """Test creating preview for a message with embed."""
        guild = DummyGuild(100)
        source_channel = DummyChannel(200)
        target_channel = DummyChannel(300)
        user = DummyUser(400)

        ctx = DummyMessage(500, guild, source_channel, user)

        # Create message with embed
        embed = DummyEmbed(title="Embed Title", description="Embed Description", color=discord.Color.blue())
        ref_message = DummyMessage(600, guild, target_channel, user, content="Message content", embeds=[embed])

        mock_result = MagicMock()
        cog.messaging.send_embed = AsyncMock(return_value=mock_result)

        await cog.create_message_preview(ctx, ref_message)

        # Verify embed was created with embed data
        call_args = cog.messaging.send_embed.call_args

        # Verify title
        assert call_args[0][1] == "Embed Title"

        # Verify message includes both content and embed description
        message_arg = call_args[1]["message"]
        assert "Message content" in message_arg
        assert "Embed Description" in message_arg

        # Verify color
        assert call_args[1]["color"] == discord.Color.blue()

    async def test_create_message_preview_with_thumbnail(self, cog):
        """Test creating preview for a message with thumbnail."""
        guild = DummyGuild(100)
        source_channel = DummyChannel(200)
        target_channel = DummyChannel(300)
        user = DummyUser(400)

        ctx = DummyMessage(500, guild, source_channel, user)

        embed = DummyEmbed(title="Test", thumbnail="https://example.com/thumb.png")
        ref_message = DummyMessage(600, guild, target_channel, user, embeds=[embed])

        cog.messaging.send_embed = AsyncMock(return_value=MagicMock())

        await cog.create_message_preview(ctx, ref_message)

        call_args = cog.messaging.send_embed.call_args
        assert call_args[1]["thumbnail"] == "https://example.com/thumb.png"

    async def test_create_message_preview_with_image(self, cog):
        """Test creating preview for a message with image."""
        guild = DummyGuild(100)
        source_channel = DummyChannel(200)
        target_channel = DummyChannel(300)
        user = DummyUser(400)

        ctx = DummyMessage(500, guild, source_channel, user)

        embed = DummyEmbed(title="Test", image="https://example.com/image.png")
        ref_message = DummyMessage(600, guild, target_channel, user, embeds=[embed])

        cog.messaging.send_embed = AsyncMock(return_value=MagicMock())

        await cog.create_message_preview(ctx, ref_message)

        call_args = cog.messaging.send_embed.call_args
        assert call_args[1]["image"] == "https://example.com/image.png"

    async def test_create_message_preview_with_fields(self, cog):
        """Test creating preview for a message with embed fields."""
        guild = DummyGuild(100)
        source_channel = DummyChannel(200)
        target_channel = DummyChannel(300)
        user = DummyUser(400)

        ctx = DummyMessage(500, guild, source_channel, user)

        field1 = DummyEmbedField("Field 1", "Value 1", inline=True)
        field2 = DummyEmbedField("Field 2", "Value 2", inline=False)
        embed = DummyEmbed(title="Test", fields=[field1, field2])
        ref_message = DummyMessage(600, guild, target_channel, user, embeds=[embed])

        cog.messaging.send_embed = AsyncMock(return_value=MagicMock())

        await cog.create_message_preview(ctx, ref_message)

        call_args = cog.messaging.send_embed.call_args
        fields = call_args[1]["fields"]

        assert len(fields) == 2
        assert fields[0]["name"] == "Field 1"
        assert fields[0]["value"] == "Value 1"
        assert fields[0]["inline"] is True
        assert fields[1]["name"] == "Field 2"
        assert fields[1]["value"] == "Value 2"
        assert fields[1]["inline"] is False

    async def test_create_message_preview_with_attachments(self, cog):
        """Test creating preview for a message with attachments."""
        guild = DummyGuild(100)
        source_channel = DummyChannel(200)
        target_channel = DummyChannel(300)
        user = DummyUser(400)

        ctx = DummyMessage(500, guild, source_channel, user)

        attachment = DummyAttachment("https://example.com/file.png")
        embed = DummyEmbed(title="Test")
        ref_message = DummyMessage(600, guild, target_channel, user, embeds=[embed], attachments=[attachment])

        cog.messaging.send_embed = AsyncMock(return_value=MagicMock())

        with patch("discord.File") as mock_file:
            await cog.create_message_preview(ctx, ref_message)

            # Verify File was created for attachment
            mock_file.assert_called_once_with("https://example.com/file.png")

            # Verify files were passed to send_embed
            call_args = cog.messaging.send_embed.call_args
            assert "files" in call_args[1]

    async def test_create_message_preview_exception_handling(self, cog):
        """Test exception handling in create_message_preview."""
        guild = DummyGuild(100)
        source_channel = DummyChannel(200)
        target_channel = DummyChannel(300)
        user = DummyUser(400)

        ctx = DummyMessage(500, guild, source_channel, user)
        ref_message = DummyMessage(600, guild, target_channel, user)

        cog.messaging.send_embed = AsyncMock(side_effect=Exception("Test error"))

        # Should raise exception
        with pytest.raises(Exception):
            await cog.create_message_preview(ctx, ref_message)

        # Verify error was logged
        cog.log.error.assert_called()

    async def test_create_message_preview_footer(self, cog):
        """Test that footer includes timestamp."""
        guild = DummyGuild(100)
        source_channel = DummyChannel(200)
        target_channel = DummyChannel(300)
        user = DummyUser(400)

        ctx = DummyMessage(500, guild, source_channel, user)
        ref_message = DummyMessage(600, guild, target_channel, user)

        cog.messaging.send_embed = AsyncMock(return_value=MagicMock())
        cog.settings.get_string = MagicMock(return_value="Created: {created}")

        await cog.create_message_preview(ctx, ref_message)

        # Verify get_string was called for footer with created parameter
        footer_call = [call for call in cog.settings.get_string.call_args_list if "message_preview_footer" in str(call)]
        assert len(footer_call) > 0
        assert "created" in footer_call[0][1]


@pytest.mark.asyncio
class TestMessagePreviewSetup:
    """Test the setup function."""

    async def test_setup_creates_cog_with_dependencies(self):
        """Test that setup function creates cog with all dependencies."""
        mock_bot = MagicMock()
        mock_bot.add_cog = AsyncMock()

        with (
            patch("bot.cogs.message_preview.Settings") as mock_settings_class,
            patch("bot.cogs.message_preview.EntityHelper") as mock_entity_class,
            patch("bot.cogs.message_preview.Messaging") as mock_messaging_class,
            patch("bot.cogs.message_preview.TrackingDatabase") as mock_tracking_class,
            patch("bot.lib.discord.ext.commands.TacobotCog.logger.Log"),
        ):
            # Configure mock settings to have log_level attribute
            mock_settings_instance = MagicMock()
            mock_settings_instance.log_level = "DEBUG"
            mock_settings_class.return_value = mock_settings_instance

            from bot.cogs.message_preview import setup

            await setup(mock_bot)

            # Verify all dependencies were instantiated
            mock_settings_class.assert_called_once()
            mock_entity_class.assert_called_once_with(mock_bot)
            mock_messaging_class.assert_called_once_with(mock_bot)
            mock_tracking_class.assert_called_once()

            # Verify cog was added to bot
            mock_bot.add_cog.assert_awaited_once()
            added_cog = mock_bot.add_cog.call_args[0][0]
            assert isinstance(added_cog, MessagePreview)
