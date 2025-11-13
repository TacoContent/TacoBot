import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.assistant import AssistantCog


@pytest.fixture
def cog(bot, tacos_db, entity_helper, settings):
    c = AssistantCog(bot=bot, tacos_db=tacos_db, entity_helper=entity_helper, settings=settings)
    c.log = MagicMock()
    c.get_cog_settings = MagicMock()
    return c


@pytest.fixture
def mock_guild():
    guild = MagicMock()
    guild.id = 12345
    guild.name = "Test Guild"
    return guild


@pytest.fixture
def mock_channel():
    channel = MagicMock()
    channel.id = 22222
    channel.name = "general"
    channel.mention = "<#22222>"
    channel.type = discord.ChannelType.text
    channel.category = MagicMock()
    channel.category.name = "General"
    channel.topic = "General discussion"
    channel.created_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    channel.send = AsyncMock()
    channel.fetch_message = AsyncMock()
    return channel


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 33333
    user.name = "TestUser"
    user.mention = "<@33333>"
    return user


@pytest.fixture
def mock_tacos_db():
    tacos_db = MagicMock()
    return tacos_db


@pytest.fixture
def mock_entity_helper():
    entity_helper = MagicMock()
    return entity_helper


@pytest.fixture
def mock_message(mock_guild, mock_channel, mock_user, bot):
    message = MagicMock()
    message.guild = mock_guild
    message.channel = mock_channel
    message.author = mock_user
    message.content = f"{bot.user.mention} What is this server about?"
    return message


class TestAssistantCog:
    def test_init(self, cog, bot, tacos_db, entity_helper, settings):
        assert cog.bot == bot
        assert cog.tacos_db == tacos_db
        assert cog.entity_helper == entity_helper
        assert cog.settings == settings
        assert cog._module == "assistant"
        assert cog._class == "AssistantCog"

    @pytest.mark.asyncio
    async def test_on_message_no_guild(self, cog, mock_message):
        mock_message.guild = None

        await cog.on_message(mock_message)

        # Should return early without doing anything
        mock_message.channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_bot_author(self, cog, mock_message, bot):
        mock_message.author = bot.user

        await cog.on_message(mock_message)

        # Should return early without doing anything
        mock_message.channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_no_bot_user(self, cog, mock_message, bot):
        bot.user = None

        await cog.on_message(mock_message)

        # Should return early without doing anything
        mock_message.channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_not_mentioned(self, cog, mock_message):
        mock_message.content = "Hello everyone!"

        await cog.on_message(mock_message)

        # Should return early without doing anything
        mock_message.channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_success(self, cog, mock_message):
        with patch.object(cog, '_ai_request', return_value="This is a test server!") as mock_ai_request:
            await cog.on_message(mock_message)

            mock_ai_request.assert_called_once_with(12345, mock_message)
            mock_message.channel.send.assert_called_once_with("This is a test server!")

    @pytest.mark.asyncio
    async def test_on_message_no_ai_response(self, cog, mock_message):
        with patch.object(cog, '_ai_request', return_value=None) as mock_ai_request:
            await cog.on_message(mock_message)

            mock_ai_request.assert_called_once_with(12345, mock_message)
            mock_message.channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_message_exception(self, cog, mock_message):
        with patch.object(cog, '_ai_request', side_effect=Exception("AI Error")):
            await cog.on_message(mock_message)

            cog.log.error.assert_called_once()
            mock_message.channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_ai_request_bot_is_author(self, cog, mock_message, bot):
        mock_message.author = bot.user

        result = await cog._ai_request(12345, mock_message)

        assert result is None

    @pytest.mark.asyncio
    async def test_ai_request_no_guild(self, cog, mock_message):
        mock_message.guild = None

        result = await cog._ai_request(12345, mock_message)

        assert result is None

    @pytest.mark.asyncio
    async def test_ai_request_no_bot_user(self, cog, mock_message, bot):
        bot.user = None

        result = await cog._ai_request(12345, mock_message)

        assert result is None

    @pytest.mark.asyncio
    async def test_ai_request_not_enabled(self, cog, mock_message):
        cog.get_cog_settings.return_value = {"enabled": False}

        result = await cog._ai_request(12345, mock_message)

        assert result is None
        cog.get_cog_settings.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_ai_request_success(self, cog, mock_message, bot):
        cog.get_cog_settings.return_value = {
            "enabled": True,
            "faq": {"channel_id": "22222", "message_id": "44444"},
            "system_prompt": "You are {bot_name} in {guild_name}",
            "model": "gpt-4",
        }

        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = "AI Response"

        with (
            patch.object(cog, '_get_message_content_for_prompt', return_value="FAQ Content") as mock_faq,
            patch.object(cog, '_get_channels', return_value=[{"id": 22222, "name": "general"}]) as mock_channels,
            patch.object(cog, '_get_user_json', return_value='{"id": 33333, "name": "TestUser"}') as mock_user_json,
            patch.object(
                cog,
                'get_settings',
                return_value={"endpoint": "https://test-endpoint.com/v1", "token": "test-token", "model": "gpt-4"},
            ) as mock_get_settings,
            patch('bot.lib.utils.str_replace', return_value="You are TacoBot in Test Guild") as mock_str_replace,
            patch('bot.cogs.assistant.OpenAIHelper') as mock_openai_helper_class,
        ):

            mock_openai_helper = MagicMock()
            mock_openai_helper.chat_completion.return_value = mock_openai_response
            mock_openai_helper.get_response_text.return_value = "AI Response"
            mock_openai_helper_class.return_value = mock_openai_helper

            result = await cog._ai_request(12345, mock_message)

            assert result == "AI Response"
            mock_faq.assert_called_once_with(channel_id=22222, message_id=44444)
            mock_channels.assert_called_once_with(12345)
            mock_user_json.assert_called_once_with(12345, mock_message.author)
            mock_get_settings.assert_called_once_with(12345, "openai")
            mock_str_replace.assert_called_once_with(
                "You are {bot_name} in {guild_name}", bot_name="TacoBot", guild_name="Test Guild"
            )
            # Verify OpenAIHelper was initialized with settings
            mock_openai_helper_class.assert_called_once_with(
                settings={"endpoint": "https://test-endpoint.com/v1", "token": "test-token", "model": "gpt-4"}
            )
            # Verify chat_completion was called
            mock_openai_helper.chat_completion.assert_called_once()
            call_args = mock_openai_helper.chat_completion.call_args
            assert len(call_args[1]['messages']) == 2
            assert call_args[1]['messages'][0]['role'] == 'system'
            assert call_args[1]['messages'][1]['role'] == 'user'
            # Verify get_response_text was called
            mock_openai_helper.get_response_text.assert_called_once_with(mock_openai_response)

    @pytest.mark.asyncio
    async def test_ai_request_default_settings(self, cog, mock_message, bot):
        cog.get_cog_settings.return_value = {"enabled": True}

        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = "AI Response"

        with (
            patch.object(cog, '_get_message_content_for_prompt', return_value="") as mock_faq,
            patch.object(cog, '_get_channels', return_value=[]),
            patch.object(cog, '_get_user_json', return_value='{}'),
            patch.object(cog, 'get_settings', return_value={"model": "gpt-3.5-turbo"}),
            patch('bot.lib.utils.str_replace', return_value=""),
            patch('bot.cogs.assistant.OpenAIHelper') as mock_openai_helper_class,
        ):

            mock_openai_helper = MagicMock()
            mock_openai_helper.chat_completion.return_value = mock_openai_response
            mock_openai_helper.get_response_text.return_value = "AI Response"
            mock_openai_helper_class.return_value = mock_openai_helper

            result = await cog._ai_request(12345, mock_message)

            assert result == "AI Response"
            # Check default FAQ settings
            mock_faq.assert_called_once_with(channel_id=948278701290840074, message_id=1243617386981232670)
            # Verify OpenAIHelper was initialized with default model settings
            mock_openai_helper_class.assert_called_once_with(settings={"model": "gpt-3.5-turbo"})

    @pytest.mark.asyncio
    async def test_ai_request_model_override_from_cog_settings(self, cog, mock_message, bot):
        """Test that model in cog_settings overrides the model from openai settings."""
        cog.get_cog_settings.return_value = {
            "enabled": True,
            "model": "gpt-4-turbo",  # This should override the openai settings model
        }

        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = "AI Response"

        with (
            patch.object(cog, '_get_message_content_for_prompt', return_value=""),
            patch.object(cog, '_get_channels', return_value=[]),
            patch.object(cog, '_get_user_json', return_value='{}'),
            patch.object(
                cog,
                'get_settings',
                return_value={
                    "endpoint": "https://api.openai.com/v1",
                    "token": "test-token",
                    "model": "gpt-3.5-turbo",  # This should be overridden
                },
            ) as mock_get_settings,
            patch('bot.lib.utils.str_replace', return_value=""),
            patch('bot.cogs.assistant.OpenAIHelper') as mock_openai_helper_class,
        ):

            mock_openai_helper = MagicMock()
            mock_openai_helper.chat_completion.return_value = mock_openai_response
            mock_openai_helper.get_response_text.return_value = "AI Response"
            mock_openai_helper_class.return_value = mock_openai_helper

            result = await cog._ai_request(12345, mock_message)

            assert result == "AI Response"
            mock_get_settings.assert_called_once_with(12345, "openai")
            # Verify OpenAIHelper was initialized with cog_settings model overriding openai settings
            mock_openai_helper_class.assert_called_once_with(
                settings={
                    "endpoint": "https://api.openai.com/v1",
                    "token": "test-token",
                    "model": "gpt-4-turbo",  # Overridden by cog_settings
                }
            )

    def test_get_user_json_success(self, cog, mock_user):
        cog.tacos_db.get_tacos_count.return_value = 42

        result = cog._get_user_json(12345, mock_user)

        expected = json.dumps({"name": "<@33333>", "id": 33333, "mention": "<@33333>", "taco_count": 42})
        assert result == expected
        cog.tacos_db.get_tacos_count.assert_called_once_with(guildId=12345, userId=33333)

    def test_get_user_json_exception(self, cog, mock_user):
        cog.tacos_db.get_tacos_count.side_effect = Exception("DB Error")

        result = cog._get_user_json(12345, mock_user)

        assert result == ""
        cog.log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_message_content_for_prompt_success(self, cog, mock_channel):
        mock_faq_message = MagicMock()
        mock_faq_message.content = "Frequently Asked Questions content"
        cog.entity_helper.get_or_fetch_channel.return_value = mock_channel
        mock_channel.fetch_message.return_value = mock_faq_message

        result = await cog._get_message_content_for_prompt(22222, 44444)

        assert result == "Frequently Asked Questions content"
        cog.entity_helper.get_or_fetch_channel.assert_called_once_with(22222)
        mock_channel.fetch_message.assert_called_once_with(44444)

    @pytest.mark.asyncio
    async def test_get_message_content_for_prompt_no_channel(self, cog):
        cog.entity_helper.get_or_fetch_channel.return_value = None

        result = await cog._get_message_content_for_prompt(22222, 44444)

        assert result == ""
        cog.entity_helper.get_or_fetch_channel.assert_called_once_with(22222)

    @pytest.mark.asyncio
    async def test_get_message_content_for_prompt_exception(self, cog, mock_channel):
        cog.entity_helper.get_or_fetch_channel.side_effect = Exception("Channel Error")

        result = await cog._get_message_content_for_prompt(22222, 44444)

        assert result == ""
        cog.log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_channels_success(self, cog, bot, mock_guild):
        # Create multiple channels with different types
        text_channel = MagicMock()
        text_channel.id = 1001
        text_channel.name = "general"
        text_channel.mention = "<#1001>"
        text_channel.type = discord.ChannelType.text
        text_channel.category = MagicMock()
        text_channel.category.name = "Text Channels"
        text_channel.topic = "General discussion"
        text_channel.created_at = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        news_channel = MagicMock()
        news_channel.id = 1002
        news_channel.name = "announcements"
        news_channel.mention = "<#1002>"
        news_channel.type = discord.ChannelType.news
        news_channel.category = None
        news_channel.topic = ""
        news_channel.created_at = datetime(2020, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        voice_channel = MagicMock()
        voice_channel.id = 1003
        voice_channel.name = "Voice Chat"
        voice_channel.type = discord.ChannelType.voice

        forum_channel = MagicMock()
        forum_channel.id = 1004
        forum_channel.name = "help"
        forum_channel.mention = "<#1004>"
        forum_channel.type = discord.ChannelType.forum
        forum_channel.category = MagicMock()
        forum_channel.category.name = "Support"
        forum_channel.topic = "Get help here"
        forum_channel.created_at = datetime(2020, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

        mock_guild.channels = [text_channel, news_channel, voice_channel, forum_channel]
        bot.guilds = [mock_guild]

        result = await cog._get_channels(12345)

        assert len(result) == 3  # voice channel should be excluded
        assert result[0] == {
            "id": 1001,
            "name": "#general",
            "mention": "<#1001>",
            "category": "Text Channels",
            "topic": "General discussion",
            "created_at": "2020-01-01T12:00:00+00:00",
        }
        assert result[1] == {
            "id": 1002,
            "name": "#announcements",
            "mention": "<#1002>",
            "category": "",
            "topic": "",
            "created_at": "2020-02-01T12:00:00+00:00",
        }
        assert result[2] == {
            "id": 1004,
            "name": "#help",
            "mention": "<#1004>",
            "category": "Support",
            "topic": "Get help here",
            "created_at": "2020-03-01T12:00:00+00:00",
        }

    @pytest.mark.asyncio
    async def test_get_channels_different_guild(self, cog, bot, mock_guild):
        other_guild = MagicMock()
        other_guild.id = 99999
        other_guild.channels = []

        mock_guild.channels = []
        bot.guilds = [other_guild, mock_guild]

        result = await cog._get_channels(12345)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_channels_exception(self, cog, bot):
        bot.guilds = None

        result = await cog._get_channels(12345)

        assert result == []
        cog.log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_channels_all_channel_types(self, cog, bot, mock_guild):
        # Test all supported channel types
        channel_types = [
            discord.ChannelType.text,
            discord.ChannelType.news,
            discord.ChannelType.forum,
            discord.ChannelType.public_thread,
            discord.ChannelType.private_thread,
            discord.ChannelType.news_thread,
        ]

        channels = []
        for idx, channel_type in enumerate(channel_types):
            ch = MagicMock()
            ch.id = 2000 + idx
            ch.name = f"channel-{idx}"
            ch.mention = f"<#{2000 + idx}>"
            ch.type = channel_type
            ch.category = None
            ch.topic = ""
            ch.created_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            channels.append(ch)

        mock_guild.channels = channels
        bot.guilds = [mock_guild]

        result = await cog._get_channels(12345)

        assert len(result) == 6  # all should be included


@pytest.mark.asyncio
async def test_setup(bot, tacos_db, entity_helper, settings):
    with (
        patch('bot.cogs.assistant.Settings', return_value=settings),
        patch('bot.cogs.assistant.TacosDatabase', return_value=tacos_db),
        patch('bot.cogs.assistant.EntityHelper', return_value=entity_helper),
        patch('bot.cogs.assistant.AssistantCog') as mock_cog_class,
    ):
        mock_cog_instance = MagicMock()
        mock_cog_class.return_value = mock_cog_instance

        from bot.cogs.assistant import setup

        await setup(bot)

        mock_cog_class.assert_called_once_with(
            bot=bot, tacos_db=tacos_db, entity_helper=entity_helper, settings=settings
        )
        bot.add_cog.assert_called_once_with(mock_cog_instance)
