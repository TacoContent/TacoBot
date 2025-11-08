from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.cogs.minecraft import MinecraftCog

# Minecraft-specific fixtures (not in conftest.py)


@pytest.fixture
def minecraft_db():
    """Mock Minecraft database."""
    db = MagicMock()
    db.get_minecraft_user = MagicMock()
    db.whitelist_minecraft_user = MagicMock()
    return db


@pytest.fixture
def context_helper():
    """Mock context helper."""
    helper = MagicMock()
    helper.create_context = MagicMock()
    return helper


@pytest.fixture
def bot():
    """Mock bot with full Discord bot structure."""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 11111
    bot.user.name = "TacoBot"
    bot.user.mention = "<@11111>"
    bot.guilds = []
    bot.add_cog = AsyncMock()
    return bot


@pytest.fixture
def prompt_helper():
    """Mock prompt helper with both ask_yes_no and ask_text."""
    h = MagicMock()
    h.ask_yes_no = AsyncMock()
    h.ask_text = AsyncMock()
    return h


# Discord entity fixtures


@pytest.fixture
def guild():
    """Mock Discord guild."""
    guild = MagicMock()
    guild.id = 12345
    guild.name = "Test Guild"
    return guild


@pytest.fixture
def channel():
    """Mock Discord channel."""
    channel = MagicMock()
    channel.id = 22222
    channel.name = "minecraft"
    channel.mention = "<#22222>"
    channel.type = discord.ChannelType.text
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def user():
    """Mock Discord user."""
    user = MagicMock()
    user.id = 33333
    user.name = "TestUser"
    user.mention = "<@33333>"
    return user


@pytest.fixture
def member(user, guild):
    """Mock Discord member."""
    member = MagicMock()
    member.id = user.id
    member.name = user.name
    member.guild = guild
    return member


@pytest.fixture
def context(guild, channel, user):
    """Mock Discord context."""
    ctx = MagicMock()
    ctx.guild = guild
    ctx.channel = channel
    ctx.author = user
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()
    return ctx


@pytest.fixture
def cog(bot, minecraft_db, tracking_db, messaging, entity_helper, context_helper, prompt_helper, settings):
    """Minecraft cog fixture using shared fixtures from conftest.py."""
    # Override settings to return mock strings for minecraft keys
    settings.get_string = MagicMock(side_effect=lambda guild_id, key, **kwargs: f"mock_{key}")

    c = MinecraftCog(
        bot=bot,
        minecraft_db=minecraft_db,
        tracking_db=tracking_db,
        messaging=messaging,
        entity_helper=entity_helper,
        context_helper=context_helper,
        prompt_helper=prompt_helper,
        settings=settings,
    )
    c.log = MagicMock()
    c.get_cog_settings = MagicMock()
    return c


class TestMinecraftCogInit:
    """Tests for MinecraftCog initialization."""

    def test_init(
        self, cog, bot, minecraft_db, tracking_db, messaging, entity_helper, context_helper, prompt_helper, settings
    ):
        assert cog.bot == bot
        assert cog.minecraft_db == minecraft_db
        assert cog.tracking_db == tracking_db
        assert cog.messaging == messaging
        assert cog.entity_helper == entity_helper
        assert cog.context_helper == context_helper
        assert cog.prompt_helper == prompt_helper
        assert cog.settings == settings
        assert cog._module == "minecraft"
        assert cog._class == "MinecraftCog"
        assert cog.SELF_DESTRUCT_TIMEOUT == 30

    def test_init_default_api_endpoints(
        self, bot, minecraft_db, tracking_db, messaging, entity_helper, context_helper, prompt_helper, settings
    ):
        """Test that default API endpoints are set correctly."""
        c = MinecraftCog(
            bot=bot,
            minecraft_db=minecraft_db,
            tracking_db=tracking_db,
            messaging=messaging,
            entity_helper=entity_helper,
            context_helper=context_helper,
            prompt_helper=prompt_helper,
            settings=settings,
        )
        c.log = MagicMock()
        c.get_cog_settings = MagicMock()

        assert c.minecraft_api_base == MinecraftCog.DEFAULT_MINECRAFT_API_BASE
        assert c.player_db_api == MinecraftCog.DEFAULT_PLAYER_DB_API
        assert c.avatar_api == MinecraftCog.DEFAULT_AVATAR_API

    def test_init_custom_api_endpoints(
        self, bot, minecraft_db, tracking_db, messaging, entity_helper, context_helper, prompt_helper, settings
    ):
        """Test that custom API endpoints can be injected for testing."""
        custom_api = "http://test-api.local:8080"
        custom_player_db = "https://test-playerdb.com/api"
        custom_avatar = "https://test-avatars.com/render"

        c = MinecraftCog(
            bot=bot,
            minecraft_db=minecraft_db,
            tracking_db=tracking_db,
            messaging=messaging,
            entity_helper=entity_helper,
            context_helper=context_helper,
            prompt_helper=prompt_helper,
            settings=settings,
            minecraft_api_base=custom_api,
            player_db_api=custom_player_db,
            avatar_api=custom_avatar,
        )
        c.log = MagicMock()
        c.get_cog_settings = MagicMock()

        assert c.minecraft_api_base == custom_api
        assert c.player_db_api == custom_player_db
        assert c.avatar_api == custom_avatar


class TestMinecraftCogHelperMethods:
    """Tests for helper methods."""

    def test_clean_username(self, cog):
        assert cog._clean_username("  TestUser  ") == "testuser"
        assert cog._clean_username("TestUser") == "testuser"
        assert cog._clean_username("TEST_USER") == "test_user"

    @patch('bot.cogs.minecraft.requests.get')
    def test_api_calls_use_injected_endpoints(
        self,
        mock_get,
        bot,
        minecraft_db,
        tracking_db,
        messaging,
        entity_helper,
        context_helper,
        prompt_helper,
        settings,
    ):
        """Test that API calls use injected custom endpoints - demonstrating improved testability."""
        custom_base = "http://test-server.local:9999"
        custom_player = "https://test-player-api.test/lookup"

        test_cog = MinecraftCog(
            bot=bot,
            minecraft_db=minecraft_db,
            tracking_db=tracking_db,
            messaging=messaging,
            entity_helper=entity_helper,
            context_helper=context_helper,
            prompt_helper=prompt_helper,
            settings=settings,
            minecraft_api_base=custom_base,
            player_db_api=custom_player,
        )
        test_cog.log = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Test that status API uses custom base
        test_cog._call_minecraft_status_api()
        mock_get.assert_called_with(f"{custom_base}/tacobot/minecraft/status")

        mock_get.reset_mock()

        # Test that player DB uses custom endpoint
        test_cog._call_player_db_api("TestPlayer")
        mock_get.assert_called_with(f"{custom_player}/testplayer")

    @patch('bot.cogs.minecraft.requests.post')
    def test_call_minecraft_start_api(self, mock_post, cog):
        """Test the start API wrapper method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = cog._call_minecraft_start_api()

        assert result == mock_response
        mock_post.assert_called_once_with(f"{cog.minecraft_api_base}/taco/minecraft/server/start")

    @patch('bot.cogs.minecraft.requests.post')
    def test_call_minecraft_stop_api(self, mock_post, cog):
        """Test the stop API wrapper method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = cog._call_minecraft_stop_api()

        assert result == mock_response
        mock_post.assert_called_once_with(f"{cog.minecraft_api_base}/taco/minecraft/server/stop")

    @patch('bot.cogs.minecraft.requests.get')
    def test_call_player_db_api(self, mock_get, cog):
        """Test the player lookup API wrapper method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = cog._call_player_db_api("TestUser")

        assert result == mock_response
        # Should clean the username before calling
        mock_get.assert_called_once_with(f"{cog.player_db_api}/testuser")

    @patch('bot.cogs.minecraft.requests.get')
    def test_call_minecraft_status_api(self, mock_get, cog):
        """Test the status API wrapper method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = cog._call_minecraft_status_api()

        assert result == mock_response
        mock_get.assert_called_once_with(f"{cog.minecraft_api_base}/tacobot/minecraft/status")

    @pytest.mark.asyncio
    async def test_determine_output_channel_matches(self, cog, context, entity_helper):
        """Test output channel determination when configured channel matches context channel."""
        cog_settings = {"output_channel": 22222}
        entity_helper.get_or_fetch_channel.return_value = context.channel

        output_channel, timeout = await cog._determine_output_channel(context, cog_settings)

        # When channels match, it should use the channel itself
        assert output_channel == context.channel
        assert timeout == cog.SELF_DESTRUCT_TIMEOUT

    @pytest.mark.asyncio
    async def test_determine_output_channel_no_match(self, cog, context, entity_helper):
        """Test output channel determination when configured channel doesn't match context channel."""
        cog_settings = {"output_channel": 99999}
        different_channel = MagicMock()
        different_channel.id = 99999
        entity_helper.get_or_fetch_channel.return_value = different_channel

        output_channel, timeout = await cog._determine_output_channel(context, cog_settings)

        assert output_channel == context.author
        assert timeout is None

    @pytest.mark.asyncio
    async def test_determine_output_channel_not_found(self, cog, context, entity_helper):
        """Test output channel determination when channel is not found."""
        cog_settings = {"output_channel": 0}
        entity_helper.get_or_fetch_channel.return_value = None

        output_channel, timeout = await cog._determine_output_channel(context, cog_settings)

        assert output_channel == context.author
        assert timeout is None

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_success(self, cog, context):
        """Test successful message deletion."""
        context.message.delete = AsyncMock()

        result = await cog._safe_delete_context_message(context)

        assert result is True
        context.message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_no_message(self, cog, context):
        """Test message deletion when message is None."""
        context.message = None

        result = await cog._safe_delete_context_message(context)

        assert result is True

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_not_found(self, cog, context):
        """Test message deletion when message is already deleted."""
        context.message.delete = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Message not found"))

        result = await cog._safe_delete_context_message(context)

        assert result is False
        context.message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_forbidden(self, cog, context):
        """Test message deletion when bot lacks permissions."""
        context.message.delete = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Missing permissions"))

        result = await cog._safe_delete_context_message(context)

        assert result is False
        context.message.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_delete_context_message_http_exception(self, cog, context):
        """Test message deletion when a Discord HTTP error occurs."""
        context.message.delete = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "Server error"))

        result = await cog._safe_delete_context_message(context)

        assert result is False
        context.message.delete.assert_called_once()

    def test_build_status_fields_online_server(self, cog, settings):
        """Test building status fields for an online server."""
        guild_id = 12345
        status = {'online': True, 'players': {'online': 5, 'max': 20}, 'version': '1.19.2', 'title': 'Test Server'}
        cog_settings = {
            'server': 'test.server.com',
            'forge_version': '43.2.0',
            'mods': [{'name': 'ModA', 'version': '1.0'}, {'name': 'ModB', 'version': '2.0'}],
        }

        fields = cog._build_status_fields(guild_id, status, cog_settings)

        # Should have 5 base fields + 2 mods (no offline message)
        assert len(fields) == 7
        # Check base fields are present
        assert any('test.server.com' in f['value'] for f in fields)
        assert any('5/20' in f['value'] for f in fields)
        assert any('1.19.2' in f['value'] for f in fields)
        assert any('43.2.0' in f['value'] for f in fields)
        # Check mods are added
        assert any(f['name'] == 'ModA' and f['value'] == '1.0' for f in fields)
        assert any(f['name'] == 'ModB' and f['value'] == '2.0' for f in fields)

    def test_build_status_fields_offline_server(self, cog, settings):
        """Test building status fields for an offline server."""
        guild_id = 12345
        status = {'online': False, 'players': {'online': 0, 'max': 20}, 'version': '1.19.2', 'title': 'Test Server'}
        cog_settings = {'server': 'test.server.com', 'forge_version': '43.2.0', 'mods': []}

        fields = cog._build_status_fields(guild_id, status, cog_settings)

        # Should have 5 base fields + 1 offline message
        assert len(fields) == 6
        # Check offline message is included
        assert any('offline' in f['value'].lower() for f in fields)

    def test_build_status_fields_no_mods(self, cog, settings):
        """Test building status fields with no mods."""
        guild_id = 12345
        status = {'online': True, 'players': {'online': 0, 'max': 20}, 'version': '1.19.2', 'title': 'Test Server'}
        cog_settings = {'server': 'test.server.com', 'forge_version': '43.2.0', 'mods': []}

        fields = cog._build_status_fields(guild_id, status, cog_settings)

        # Should have exactly 5 base fields
        assert len(fields) == 5

    def test_process_player_data_success(self, cog):
        """Test processing valid player data from PlayerDB API."""
        api_response = {
            "success": True,
            "code": "player.found",
            "data": {
                "player": {
                    "id": "1b313cdd-7465-4227-95aa-ca5503beba85",
                    "raw_id": "1b313cdd7465422795aaca5503beba85",
                    "username": "TestPlayer",
                    "meta": {
                        "name_history": [{"name": "OldName"}, {"name": "TestPlayer", "changedToAt": 1577518972000}]
                    },
                }
            },
        }

        result = cog._process_player_data(api_response)

        assert result is not None
        assert result["uuid"] == "1b313cdd-7465-4227-95aa-ca5503beba85"
        assert result["raw_id"] == "1b313cdd7465422795aaca5503beba85"
        assert result["username"] == "TestPlayer"
        assert len(result["name_history"]) == 2
        assert result["avatar_url"] == f"{cog.avatar_api}/1b313cdd7465422795aaca5503beba85"

    def test_process_player_data_not_found(self, cog):
        """Test processing player data when player is not found."""
        api_response = {"success": False, "code": "player.notfound"}

        result = cog._process_player_data(api_response)

        assert result is None

    def test_process_player_data_invalid_code(self, cog):
        """Test processing player data with invalid response code."""
        api_response = {"success": True, "code": "player.error"}

        result = cog._process_player_data(api_response)

        assert result is None

    def test_process_player_data_missing_player_data(self, cog):
        """Test processing player data when player data is missing."""
        api_response = {"success": True, "code": "player.found", "data": {}}

        result = cog._process_player_data(api_response)

        assert result is None

    def test_process_player_data_missing_required_fields(self, cog):
        """Test processing player data when required fields are missing."""
        api_response = {
            "success": True,
            "code": "player.found",
            "data": {
                "player": {
                    "username": "TestPlayer"
                    # Missing id and raw_id
                }
            },
        }

        result = cog._process_player_data(api_response)

        assert result is None

    def test_is_user_whitelisted_true(self, cog, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = {"whitelist": True, "username": "TestUser", "uuid": "test-uuid"}

        result = cog._is_user_whitelisted(guild_id=12345, user_id=33333)

        assert result is True
        minecraft_db.get_minecraft_user.assert_called_once_with(guildId=12345, userId=33333)

    def test_is_user_whitelisted_false_not_whitelisted(self, cog, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = {"whitelist": False, "username": "TestUser", "uuid": "test-uuid"}

        result = cog._is_user_whitelisted(guild_id=12345, user_id=33333)

        assert result is False

    def test_is_user_whitelisted_false_no_user(self, cog, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = None

        result = cog._is_user_whitelisted(guild_id=12345, user_id=33333)

        assert result is False

    @patch('bot.cogs.minecraft.requests.get')
    def test_get_minecraft_status_success(self, mock_get, cog):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "online": True,
            "players": {"online": 5, "max": 20},
            "version": "1.19.2",
            "title": "Test Server",
        }
        mock_get.return_value = mock_response

        result = cog._get_minecraft_status(guild_id=12345)

        assert result["success"] is True
        assert result["online"] is True
        assert result["players"]["online"] == 5
        mock_get.assert_called_once_with("http://andeddu.bit13.local:10070/tacobot/minecraft/status")

    @patch('bot.cogs.minecraft.requests.get')
    def test_get_minecraft_status_failure(self, mock_get, cog):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Failed to get minecraft status"):
            cog._get_minecraft_status(guild_id=12345)

        cog.log.warn.assert_called_once()


class TestMinecraftCogOnMemberRemove:
    """Tests for on_member_remove event listener."""

    @pytest.mark.asyncio
    async def test_on_member_remove_whitelisted_user(self, cog, member, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = {"whitelist": True, "username": "TestUser", "uuid": "test-uuid"}

        await cog.on_member_remove(member)

        # Called twice: once in _is_user_whitelisted, once to get user details
        assert minecraft_db.get_minecraft_user.call_count == 2
        minecraft_db.whitelist_minecraft_user.assert_called_once_with(
            guildId=12345, userId=33333, username="TestUser", uuid="test-uuid", whitelist=False
        )
        cog.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_on_member_remove_not_whitelisted(self, cog, member, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = {"whitelist": False, "username": "TestUser", "uuid": "test-uuid"}

        await cog.on_member_remove(member)

        minecraft_db.whitelist_minecraft_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_member_remove_no_mc_user(self, cog, member, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = None

        await cog.on_member_remove(member)

        minecraft_db.whitelist_minecraft_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_member_remove_exception(self, cog, member, minecraft_db):
        minecraft_db.get_minecraft_user.side_effect = Exception("Database error")

        await cog.on_member_remove(member)

        cog.log.error.assert_called_once()


class TestMinecraftCogStatusCommand:
    """Tests for minecraft status command."""

    @pytest.mark.asyncio
    async def test_status_disabled_cog(self, cog, context):
        cog.get_cog_settings.return_value = {"enabled": False}

        await cog.status(context)

        cog.log.debug.assert_called()
        cog.messaging.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_status_user_not_whitelisted(self, cog, context, entity_helper, minecraft_db):
        cog.get_cog_settings.return_value = {"enabled": True, "output_channel": 22222}
        entity_helper.get_or_fetch_channel.return_value = context.channel
        minecraft_db.get_minecraft_user.return_value = None

        await cog.status(context)

        cog.messaging.send_embed.assert_called_once()
        call_args = cog.messaging.send_embed.call_args
        # Channel should be the same mock from get_or_fetch_channel since output_channel matches ctx.channel
        assert "title" in call_args[1]

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.get')
    async def test_status_success_server_online(self, mock_get, cog, context, entity_helper, minecraft_db, tracking_db):
        cog.get_cog_settings.return_value = {
            "enabled": True,
            "output_channel": 22222,
            "server": "test.server.com",
            "forge_version": "40.1.0",
            "mods": [{"name": "Mod1", "version": "1.0.0"}],
            "help": "Help text",
        }
        entity_helper.get_or_fetch_channel.return_value = context.channel
        minecraft_db.get_minecraft_user.return_value = {"whitelist": True, "username": "TestUser", "uuid": "test-uuid"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "online": True,
            "players": {"online": 5, "max": 20},
            "version": "1.19.2",
            "title": "Test Server",
        }
        mock_get.return_value = mock_response

        await cog.status(context)

        cog.messaging.send_embed.assert_called_once()
        call_args = cog.messaging.send_embed.call_args
        assert "fields" in call_args[1]
        tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.get')
    async def test_status_success_server_offline(self, mock_get, cog, context, entity_helper, minecraft_db):
        cog.get_cog_settings.return_value = {
            "enabled": True,
            "output_channel": 22222,
            "server": "test.server.com",
            "forge_version": "40.1.0",
            "mods": [],
            "help": "Help text",
        }
        entity_helper.get_or_fetch_channel.return_value = context.channel
        minecraft_db.get_minecraft_user.return_value = {"whitelist": True, "username": "TestUser", "uuid": "test-uuid"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "online": False,
            "players": {"online": 0, "max": 20},
            "version": "1.19.2",
            "title": "Test Server",
        }
        mock_get.return_value = mock_response

        await cog.status(context)

        cog.messaging.send_embed.assert_called_once()
        call_args = cog.messaging.send_embed.call_args
        fields = call_args[1]["fields"]
        # Check that offline message field was added
        assert any("offline" in str(field).lower() for field in fields)

    @pytest.mark.asyncio
    async def test_status_exception(self, cog, context, messaging):
        cog.get_cog_settings.side_effect = Exception("Settings error")

        await cog.status(context)

        cog.log.error.assert_called_once()
        messaging.notify_of_error.assert_called_once_with(context)


class TestMinecraftCogStartCommand:
    """Tests for minecraft start command."""

    @pytest.mark.asyncio
    async def test_start_user_not_whitelisted(self, cog, context, entity_helper, minecraft_db):
        cog.get_cog_settings.return_value = {"enabled": True, "output_channel": 22222}
        entity_helper.get_or_fetch_channel.return_value = context.channel
        minecraft_db.get_minecraft_user.return_value = None

        # Call the callback directly to bypass the decorator
        await cog.start_server.callback(cog, context)

        cog.messaging.send_embed.assert_called_once()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_control_no_start" in str(call_args)

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.get')
    async def test_start_server_already_running(self, mock_get, cog, context, entity_helper, minecraft_db):
        cog.get_cog_settings.return_value = {"enabled": True, "output_channel": 22222}
        entity_helper.get_or_fetch_channel.return_value = context.channel
        minecraft_db.get_minecraft_user.return_value = {"whitelist": True, "username": "TestUser", "uuid": "test-uuid"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "online": True}
        mock_get.return_value = mock_response

        await cog.start_server.callback(cog, context)

        cog.messaging.send_embed.assert_called_once()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_control_running" in str(call_args)

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.post')
    @patch('bot.cogs.minecraft.requests.get')
    async def test_start_server_success(
        self, mock_get, mock_post, cog, context, entity_helper, minecraft_db, tracking_db
    ):
        cog.get_cog_settings.return_value = {"enabled": True, "output_channel": 22222}
        entity_helper.get_or_fetch_channel.return_value = context.channel
        minecraft_db.get_minecraft_user.return_value = {"whitelist": True, "username": "TestUser", "uuid": "test-uuid"}

        mock_status_response = MagicMock()
        mock_status_response.status_code = 200
        mock_status_response.json.return_value = {"success": True, "online": False}
        mock_get.return_value = mock_status_response

        mock_start_response = MagicMock()
        mock_start_response.status_code = 200
        mock_start_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_start_response

        await cog.start_server.callback(cog, context)

        mock_post.assert_called_once_with("http://andeddu.bit13.local:10070/taco/minecraft/server/start")
        cog.messaging.send_embed.assert_called()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_control_start_success" in str(call_args)
        tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.post')
    @patch('bot.cogs.minecraft.requests.get')
    async def test_start_server_http_error(self, mock_get, mock_post, cog, context, entity_helper, minecraft_db):
        cog.get_cog_settings.return_value = {"enabled": True, "output_channel": 22222}
        entity_helper.get_or_fetch_channel.return_value = context.channel
        minecraft_db.get_minecraft_user.return_value = {"whitelist": True, "username": "TestUser", "uuid": "test-uuid"}

        mock_status_response = MagicMock()
        mock_status_response.status_code = 200
        mock_status_response.json.return_value = {"success": True, "online": False}
        mock_get.return_value = mock_status_response

        mock_start_response = MagicMock()
        mock_start_response.status_code = 500
        mock_post.return_value = mock_start_response

        await cog.start_server.callback(cog, context)

        cog.messaging.send_embed.assert_called()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_control_start_failure_code" in str(call_args)

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.post')
    @patch('bot.cogs.minecraft.requests.get')
    async def test_start_server_api_error(self, mock_get, mock_post, cog, context, entity_helper, minecraft_db):
        cog.get_cog_settings.return_value = {"enabled": True, "output_channel": 22222}
        entity_helper.get_or_fetch_channel.return_value = context.channel
        minecraft_db.get_minecraft_user.return_value = {"whitelist": True, "username": "TestUser", "uuid": "test-uuid"}

        mock_status_response = MagicMock()
        mock_status_response.status_code = 200
        mock_status_response.json.return_value = {"success": True, "online": False}
        mock_get.return_value = mock_status_response

        mock_start_response = MagicMock()
        mock_start_response.status_code = 200
        mock_start_response.json.return_value = {"status": "failure", "message": "Server start failed"}
        mock_post.return_value = mock_start_response

        await cog.start_server.callback(cog, context)

        cog.messaging.send_embed.assert_called()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_control_failure" in str(call_args)


class TestMinecraftCogStopCommand:
    """Tests for minecraft stop command."""

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.get')
    async def test_stop_server_already_stopped(self, mock_get, cog, context, entity_helper):
        cog.get_cog_settings.return_value = {"enabled": True, "output_channel": 22222}
        entity_helper.get_or_fetch_channel.return_value = context.channel

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "online": False}
        mock_get.return_value = mock_response

        await cog.stop_server.callback(cog, context)

        cog.messaging.send_embed.assert_called_once()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_control_stopped" in str(call_args)

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.post')
    @patch('bot.cogs.minecraft.requests.get')
    async def test_stop_server_success(self, mock_get, mock_post, cog, context, entity_helper, tracking_db):
        cog.get_cog_settings.return_value = {"enabled": True, "output_channel": 22222}
        entity_helper.get_or_fetch_channel.return_value = context.channel

        mock_status_response = MagicMock()
        mock_status_response.status_code = 200
        mock_status_response.json.return_value = {"success": True, "online": True}
        mock_get.return_value = mock_status_response

        mock_stop_response = MagicMock()
        mock_stop_response.status_code = 200
        mock_stop_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_stop_response

        await cog.stop_server.callback(cog, context)

        mock_post.assert_called_once_with("http://andeddu.bit13.local:10070/taco/minecraft/server/stop")
        cog.messaging.send_embed.assert_called()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_control_stop_success" in str(call_args)
        tracking_db.track_command_usage.assert_called_once()


class TestMinecraftCogWhitelistCommand:
    """Tests for minecraft whitelist command."""

    @pytest.mark.asyncio
    async def test_whitelist_already_whitelisted(self, cog, context, minecraft_db):
        minecraft_db.get_minecraft_user.return_value = {"whitelist": True, "username": "TestUser", "uuid": "test-uuid"}

        await cog.whitelist.callback(cog, context)

        cog.messaging.send_embed.assert_called_once()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_whitelist_already_whitelisted_message" in str(call_args)

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.get')
    async def test_whitelist_success_with_dm(
        self, mock_get, cog, context, minecraft_db, prompt_helper, context_helper, tracking_db
    ):
        minecraft_db.get_minecraft_user.return_value = None
        prompt_helper.ask_text.return_value = "TestMCUser"

        mock_new_context = MagicMock()
        mock_new_context.channel = context.author
        context_helper.create_context.return_value = mock_new_context

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "code": "player.found",
            "data": {
                "player": {
                    "id": "test-uuid",
                    "raw_id": "testuuid",
                    "username": "TestMCUser",
                    "name_history": [{"name": "TestMCUser"}],
                }
            },
        }
        mock_get.return_value = mock_response

        await cog.whitelist.callback(cog, context)

        prompt_helper.ask_text.assert_called_once()
        mock_get.assert_called_once_with("https://playerdb.co/api/player/minecraft/testmcuser")
        prompt_helper.ask_yes_no.assert_called_once()
        # Verify whitelist was added (called twice - once in callback, once at end)
        assert minecraft_db.whitelist_minecraft_user.call_count >= 1
        tracking_db.track_command_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_whitelist_user_cancels(self, cog, context, minecraft_db, prompt_helper, context_helper):
        minecraft_db.get_minecraft_user.return_value = None
        prompt_helper.ask_text.return_value = "cancel"

        mock_new_context = MagicMock()
        mock_new_context.channel = context.author
        context_helper.create_context.return_value = mock_new_context

        await cog.whitelist.callback(cog, context)

        prompt_helper.ask_text.assert_called_once()
        minecraft_db.whitelist_minecraft_user.assert_not_called()

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.get')
    async def test_whitelist_player_not_found(
        self, mock_get, cog, context, minecraft_db, prompt_helper, context_helper
    ):
        minecraft_db.get_minecraft_user.return_value = None
        prompt_helper.ask_text.return_value = "InvalidUser"

        mock_new_context = MagicMock()
        mock_new_context.channel = context.author
        context_helper.create_context.return_value = mock_new_context

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": False, "code": "player.not_found"}
        mock_get.return_value = mock_response

        await cog.whitelist.callback(cog, context)

        cog.messaging.send_embed.assert_called()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_whitelist_unable_to_verify" in str(call_args)
        minecraft_db.whitelist_minecraft_user.assert_not_called()

    @pytest.mark.asyncio
    @patch('bot.cogs.minecraft.requests.get')
    async def test_whitelist_api_error(self, mock_get, cog, context, minecraft_db, prompt_helper, context_helper):
        minecraft_db.get_minecraft_user.return_value = None
        prompt_helper.ask_text.return_value = "TestUser"

        mock_new_context = MagicMock()
        mock_new_context.channel = context.author
        context_helper.create_context.return_value = mock_new_context

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        await cog.whitelist.callback(cog, context)

        cog.log.warn.assert_called()
        cog.messaging.send_embed.assert_called()
        call_args = cog.messaging.send_embed.call_args
        assert "minecraft_whitelist_unable_to_verify" in str(call_args)

    @pytest.mark.asyncio
    async def test_whitelist_dm_forbidden_fallback(self, cog, context, minecraft_db, prompt_helper, context_helper):
        minecraft_db.get_minecraft_user.return_value = None

        # First call raises Forbidden, second call succeeds
        prompt_helper.ask_text.side_effect = [discord.Forbidden(MagicMock(), "Cannot send DM"), "cancel"]

        mock_new_context = MagicMock()
        mock_new_context.channel = context.author
        context_helper.create_context.return_value = mock_new_context

        await cog.whitelist.callback(cog, context)

        # Should have been called twice - once for DM (failed), once for channel
        assert prompt_helper.ask_text.call_count == 2


class TestMinecraftCogMainCommand:
    """Tests for main minecraft command group."""

    @pytest.mark.asyncio
    async def test_minecraft_command_with_subcommand(self, cog, context):
        context.invoked_subcommand = "status"

        await cog.minecraft.callback(cog, context)

        # Should return early without calling status
        cog.messaging.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_minecraft_command_without_subcommand(self, cog, context, entity_helper, minecraft_db):
        context.invoked_subcommand = None
        cog.get_cog_settings.return_value = {"enabled": False}

        await cog.minecraft.callback(cog, context)

        # Should call status
        cog.log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_minecraft_command_exception(self, cog, context, messaging):
        context.invoked_subcommand = None
        cog.get_cog_settings.side_effect = Exception("Settings error")

        await cog.minecraft.callback(cog, context)

        cog.log.error.assert_called_once()
        messaging.notify_of_error.assert_called_once_with(context)
