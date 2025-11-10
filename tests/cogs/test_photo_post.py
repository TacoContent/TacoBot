"""Unit tests for PhotoPostCog.

Tests cover:
- Initialization
- on_message listener with all branches
- Guild checks, bot checks, channel config
- Photo detection (attachments vs links)
- Reactions, taco giving, tracking
- Exception handling

Target: 100% code coverage
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.cogs.photo_post import PhotoPostCog
from bot.lib.enums import tacotypes


class TestPhotoPostCogInitialization:
    """Test suite for PhotoPostCog initialization."""

    def test_init_success(self, bot, tracking_db, entity_helper, taco_helper, settings):
        """Test successful cog initialization.

        Verifies:
        - Cog initializes without errors
        - All dependencies are stored correctly
        - Logger is initialized
        """
        cog = PhotoPostCog(
            bot=bot, tracking_db=tracking_db, entity_helper=entity_helper, taco_helper=taco_helper, settings=settings
        )

        assert cog.bot == bot
        assert cog.tracking_db == tracking_db
        assert cog.entity_helper == entity_helper
        assert cog.taco_helper == taco_helper
        assert cog.settings == settings
        assert cog._module == "photo_post"
        assert cog._class == "PhotoPostCog"


class TestPhotoPostCogOnMessage:
    """Test suite for on_message listener."""

    @pytest.fixture
    def taco_helper(self):
        """Create a mock taco helper with async give_tacos method."""
        helper = MagicMock()
        helper.give_tacos = AsyncMock()
        return helper

    @pytest.fixture
    def cog(self, bot, tracking_db, entity_helper, taco_helper, settings):
        """Create a PhotoPostCog instance with mocked dependencies."""
        cog_instance = PhotoPostCog(
            bot=bot, tracking_db=tracking_db, entity_helper=entity_helper, taco_helper=taco_helper, settings=settings
        )
        cog_instance.log = MagicMock()
        cog_instance.log.debug = MagicMock()
        cog_instance.log.error = MagicMock()
        return cog_instance

    @pytest.fixture
    def message(self):
        """Create a mock Discord message."""
        m = MagicMock()
        m.guild = MagicMock()
        m.guild.id = 12345
        m.author = MagicMock()
        m.author.bot = False
        m.author.id = 67890
        m.author.name = "TestUser"
        m.channel = MagicMock()
        m.channel.id = 111
        m.channel.name = "photos"
        m.attachments = []
        m.content = ""
        m.id = 222
        m.add_reaction = AsyncMock()
        return m

    @pytest.mark.asyncio
    async def test_on_message_no_guild(self, cog, message):
        """Test that listener returns early when message has no guild.

        Verifies:
        - Function returns immediately
        - No tacos are given
        - No tracking occurs
        """
        message.guild = None
        await cog.on_message(message)
        cog.taco_helper.give_tacos.assert_not_called()
        cog.tracking_db.track_photo_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_guild_id_zero(self, cog, message):
        """Test that listener returns early when guild_id is 0.

        Verifies:
        - Function returns immediately
        - No tacos are given
        - No tracking occurs
        """
        message.guild.id = 0
        await cog.on_message(message)
        cog.taco_helper.give_tacos.assert_not_called()
        cog.tracking_db.track_photo_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_author_is_bot(self, cog, message):
        """Test that listener ignores messages from bots.

        Verifies:
        - Function returns early for bot messages
        - No tacos are given
        - No tracking occurs
        """
        message.author.bot = True
        await cog.on_message(message)
        cog.taco_helper.give_tacos.assert_not_called()
        cog.tracking_db.track_photo_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_channel_not_allowed(self, cog, message):
        """Test that listener ignores messages in non-configured channels.

        Verifies:
        - get_cog_settings is called
        - Function returns early for unconfigured channels
        - No tacos are given
        """
        cog.get_cog_settings = MagicMock(return_value={"channels": []})
        await cog.on_message(message)
        cog.get_cog_settings.assert_called_once_with(message.guild.id)
        cog.taco_helper.give_tacos.assert_not_called()
        cog.tracking_db.track_photo_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_not_photo(self, cog, message):
        """Test that listener ignores messages without photos.

        Verifies:
        - Channel is checked and allowed
        - Message is checked for photos
        - Debug log is called
        - No tacos are given
        """
        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": str(message.channel.id), "reactions": ["👍"], "tacos": 5}]}
        )
        message.attachments = []
        message.content = "no image here"
        await cog.on_message(message)
        cog.log.debug.assert_called()
        cog.taco_helper.give_tacos.assert_not_called()
        cog.tracking_db.track_photo_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_photo_attachment(self, cog, message, bot):
        """Test successful photo post with attachment.

        Verifies:
        - Reactions are added to message
        - Tacos are given with correct parameters
        - Photo post is tracked in database
        """
        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": str(message.channel.id), "reactions": ["👍", "❤️"], "tacos": 7}]}
        )
        attachment = MagicMock()
        attachment.url = "https://cdn.discordapp.com/attachments/1/2/photo.png"
        message.attachments = [attachment]
        message.content = ""

        await cog.on_message(message)

        message.add_reaction.assert_any_call("👍")
        message.add_reaction.assert_any_call("❤️")
        cog.taco_helper.give_tacos.assert_awaited_once_with(
            guildId=message.guild.id,
            fromUser=bot.user,
            toUser=message.author,
            reason=f"Photo post in #{message.channel.name}",
            give_type=tacotypes.TacoTypes.PHOTO_POST,
            taco_amount=7,
        )
        cog.tracking_db.track_photo_post.assert_called_once_with(
            guildId=message.guild.id,
            userId=message.author.id,
            messageId=message.id,
            channelId=message.channel.id,
            message=message.content,
            image=attachment.url,
            channelName=message.channel.name,
        )

    @pytest.mark.asyncio
    async def test_on_message_photo_link(self, cog, message, bot):
        """Test successful photo post with Discord CDN link.

        Verifies:
        - Regex matches Discord CDN URLs
        - Reactions are added
        - Tacos are given
        - Photo post is tracked with URL from content
        """
        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": str(message.channel.id), "reactions": ["👍"], "tacos": 3}]}
        )
        message.attachments = []
        message.content = "https://cdn.discordapp.com/attachments/123/456/photo.jpg"

        await cog.on_message(message)

        message.add_reaction.assert_called_with("👍")
        cog.taco_helper.give_tacos.assert_awaited_once_with(
            guildId=message.guild.id,
            fromUser=bot.user,
            toUser=message.author,
            reason=f"Photo post in #{message.channel.name}",
            give_type=tacotypes.TacoTypes.PHOTO_POST,
            taco_amount=3,
        )
        cog.tracking_db.track_photo_post.assert_called_once()
        # Verify the image URL from regex match was used
        call_args = cog.tracking_db.track_photo_post.call_args
        assert "cdn.discordapp.com" in call_args.kwargs["image"]

    @pytest.mark.asyncio
    async def test_on_message_photo_media_link(self, cog, message, bot):
        """Test photo post with media.discordapp.com link.

        Verifies:
        - Regex matches media.discordapp.com URLs
        - Tacos are given
        - Tracking occurs
        """
        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": str(message.channel.id), "reactions": ["🎨"], "tacos": 4}]}
        )
        message.attachments = []
        message.content = "https://media.discordapp.net/attachments/789/012/image.png"

        await cog.on_message(message)

        message.add_reaction.assert_called_with("🎨")
        cog.taco_helper.give_tacos.assert_awaited_once()
        cog.tracking_db.track_photo_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_message_photo_default_tacos(self, cog, message, bot):
        """Test that default taco amount (5) is used when tacos is 0.

        Verifies:
        - Tacos value of 0 triggers default behavior
        - Default amount (5) is used instead
        """
        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": str(message.channel.id), "reactions": ["👍"], "tacos": 0}]}
        )
        message.attachments = [MagicMock(url="https://cdn.discordapp.com/attachments/1/2/photo.png")]

        await cog.on_message(message)

        cog.taco_helper.give_tacos.assert_awaited_once_with(
            guildId=message.guild.id,
            fromUser=bot.user,
            toUser=message.author,
            reason=f"Photo post in #{message.channel.name}",
            give_type=tacotypes.TacoTypes.PHOTO_POST,
            taco_amount=5,  # Default when tacos is 0
        )
        cog.tracking_db.track_photo_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_message_photo_missing_tacos_key(self, cog, message, bot):
        """Test that default taco amount (5) is used when tacos key is missing.

        Verifies:
        - Missing 'tacos' key triggers default behavior
        - Default amount (5) is used
        """
        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": str(message.channel.id), "reactions": ["👍"]}]}
        )
        message.attachments = [MagicMock(url="https://cdn.discordapp.com/attachments/1/2/photo.png")]

        await cog.on_message(message)

        cog.taco_helper.give_tacos.assert_awaited_once()
        call_args = cog.taco_helper.give_tacos.call_args
        assert call_args.kwargs["taco_amount"] == 5

    @pytest.mark.asyncio
    async def test_on_message_exception_during_reaction(self, cog, message):
        """Test that exceptions during add_reaction are caught and logged.

        Verifies:
        - Exception doesn't crash the listener
        - Error is logged with traceback
        """
        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": str(message.channel.id), "reactions": ["👍"], "tacos": 5}]}
        )
        message.attachments = [MagicMock(url="https://cdn.discordapp.com/attachments/1/2/photo.png")]
        message.add_reaction.side_effect = Exception("Reaction failed")

        await cog.on_message(message)

        cog.log.error.assert_called_once()
        # Verify error message contains the exception
        error_call_args = cog.log.error.call_args
        assert "Reaction failed" in str(error_call_args)

    @pytest.mark.asyncio
    async def test_on_message_exception_during_give_tacos(self, cog, message):
        """Test that exceptions during give_tacos are caught and logged.

        Verifies:
        - Exception doesn't crash the listener
        - Error is logged
        """
        cog.get_cog_settings = MagicMock(
            return_value={"channels": [{"id": str(message.channel.id), "reactions": ["👍"], "tacos": 5}]}
        )
        message.attachments = [MagicMock(url="https://cdn.discordapp.com/attachments/1/2/photo.png")]
        cog.taco_helper.give_tacos.side_effect = Exception("Database error")

        await cog.on_message(message)

        cog.log.error.assert_called_once()
        error_call_args = cog.log.error.call_args
        assert "Database error" in str(error_call_args)


class TestPhotoPostCogSetup:
    """Test suite for async setup function."""

    @pytest.mark.asyncio
    async def test_setup_success(self):
        """Test successful cog setup and registration with bot.

        Verifies:
        - All dependencies are created
        - PhotoPostCog is instantiated with correct parameters
        - bot.add_cog is called with the cog instance
        """
        from unittest.mock import patch

        from bot.cogs.photo_post import setup

        bot = MagicMock()
        bot.add_cog = AsyncMock()

        with (
            patch("bot.cogs.photo_post.Settings") as MockSettings,
            patch("bot.cogs.photo_post.TrackingDatabase") as MockTrackingDB,
            patch("bot.cogs.photo_post.EntityHelper") as MockEntityHelper,
            patch("bot.cogs.photo_post.TacoHelper") as MockTacoHelper,
        ):
            mock_settings = MagicMock()
            mock_settings.log_level = "INFO"
            MockSettings.return_value = mock_settings

            mock_tracking_db = MagicMock()
            MockTrackingDB.return_value = mock_tracking_db

            mock_entity_helper = MagicMock()
            MockEntityHelper.return_value = mock_entity_helper

            mock_taco_helper = MagicMock()
            MockTacoHelper.return_value = mock_taco_helper

            await setup(bot)

            MockSettings.assert_called_once()
            MockTrackingDB.assert_called_once()
            MockEntityHelper.assert_called_once_with(bot)
            MockTacoHelper.assert_called_once_with(bot, entity_helper=mock_entity_helper)

            bot.add_cog.assert_awaited_once()
            args, kwargs = bot.add_cog.call_args
            assert isinstance(args[0], PhotoPostCog)
            assert args[0].bot == bot
            assert args[0].settings == mock_settings
            assert args[0].tracking_db == mock_tracking_db
            assert args[0].entity_helper == mock_entity_helper
            assert args[0].taco_helper == mock_taco_helper
