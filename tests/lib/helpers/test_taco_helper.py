"""Tests for TacoHelper class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.lib.enums import tacotypes
from bot.lib.helpers.taco_helper import TacoHelper


class TestTacoHelper:
    """Test suite for TacoHelper."""

    @pytest.fixture
    def taco_helper(self, bot, entity_helper, settings):
        with (
            patch('bot.lib.helpers.taco_helper.Settings') as mock_settings_class,
            patch('bot.lib.helpers.taco_helper.TacosDatabase') as mock_db_class,
            patch('bot.lib.helpers.taco_helper.MessageHelper') as mock_message_helper_class,
        ):
            settings.log_level = "DEBUG"
            settings.get_string = MagicMock(return_value="test string")
            settings.get_settings = MagicMock(
                return_value={"taco_log_channel_id": "12345", "taco_reaction_count": 5, "taco_custom_count": 1}
            )
            mock_settings_class.return_value = settings
            mock_db = MagicMock()
            mock_db.add_tacos = MagicMock(return_value=10)
            mock_db.track_tacos_log = MagicMock()
            mock_db_class.return_value = mock_db
            mock_message_helper_class = MagicMock()
            mock_message_helper_class.send_embed = AsyncMock()
            mock_message_helper_class.return_value = mock_message_helper_class
            helper = TacoHelper(bot, entity_helper=entity_helper)
            return helper

    @pytest.fixture
    def mock_from_user(self):
        user = MagicMock()
        user.id = 111
        user.name = "FromUser"
        user.display_name = "FromUser"
        return user

    @pytest.fixture
    def mock_to_user(self):
        user = MagicMock()
        user.id = 222
        user.name = "ToUser"
        user.display_name = "ToUser"
        return user

    def test_get_taco_settings_success(self, taco_helper):
        settings = taco_helper.get_taco_settings(guildId=999)
        assert settings is not None
        assert "taco_log_channel_id" in settings
        assert settings["taco_log_channel_id"] == "12345"

    def test_get_taco_settings_no_settings(self, taco_helper):
        taco_helper.settings.get_settings = MagicMock(return_value=None)
        with pytest.raises(Exception, match="No tacos settings found for guild 999"):
            taco_helper.get_taco_settings(guildId=999)

    @pytest.mark.asyncio
    async def test_give_tacos_basic(self, taco_helper, mock_from_user, mock_to_user):
        total = await taco_helper.give_tacos(
            guildId=999,
            fromUser=mock_from_user,
            toUser=mock_to_user,
            reason="Good job!",
            give_type=tacotypes.TacoTypes.CUSTOM,
            taco_amount=1,
        )
        assert total == 10
        taco_helper.tacos_db.add_tacos.assert_called_once_with(999, 222, 1)
        taco_helper.tacos_db.track_tacos_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_give_tacos_no_reason(self, taco_helper, mock_from_user, mock_to_user):
        total = await taco_helper.give_tacos(
            guildId=999,
            fromUser=mock_from_user,
            toUser=mock_to_user,
            reason=None,
            give_type=tacotypes.TacoTypes.CUSTOM,
            taco_amount=1,
        )
        assert total == 10

    @pytest.mark.asyncio
    async def test_give_tacos_uses_settings_amount(self, taco_helper, mock_from_user, mock_to_user):
        taco_helper.settings.get_settings = MagicMock(
            return_value={"taco_log_channel_id": "12345", "taco_reaction_count": 5}
        )
        with patch.object(tacotypes.TacoTypes, 'get_string_from_taco_type', return_value='taco_reaction_count'):
            await taco_helper.give_tacos(
                guildId=999,
                fromUser=mock_from_user,
                toUser=mock_to_user,
                reason="Reacted to message",
                give_type=tacotypes.TacoTypes.REACTION,
                taco_amount=1,
            )
            taco_helper.tacos_db.add_tacos.assert_called_once_with(999, 222, 5)

    @pytest.mark.asyncio
    async def test_give_tacos_fallback_to_taco_amount(self, taco_helper, mock_from_user, mock_to_user):
        with patch.object(tacotypes.TacoTypes, 'get_string_from_taco_type', return_value='unknown_type'):
            await taco_helper.give_tacos(
                guildId=999,
                fromUser=mock_from_user,
                toUser=mock_to_user,
                reason="Custom action",
                give_type=tacotypes.TacoTypes.CUSTOM,
                taco_amount=3,
            )
            taco_helper.tacos_db.add_tacos.assert_called_once_with(999, 222, 3)

    @pytest.mark.asyncio
    async def test_give_tacos_exception_handling(self, taco_helper, mock_from_user, mock_to_user):
        taco_helper.tacos_db.add_tacos = MagicMock(side_effect=Exception("Database error"))
        total = await taco_helper.give_tacos(
            guildId=999,
            fromUser=mock_from_user,
            toUser=mock_to_user,
            reason="Test",
            give_type=tacotypes.TacoTypes.CUSTOM,
            taco_amount=1,
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_log_taco_transaction_positive_count(self, taco_helper, mock_from_user, mock_to_user, entity_helper):
        mock_channel = MagicMock()
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        await taco_helper.log_taco_transaction(
            guild_id=999,
            toMember=mock_to_user,
            fromMember=mock_from_user,
            count=5,
            total_tacos=15,
            reason="Good work",
            type=tacotypes.TacoTypes.CUSTOM,
        )
        taco_helper.message_helper.send_embed.assert_called_once()
        call_kwargs = taco_helper.message_helper.send_embed.call_args.kwargs
        assert call_kwargs['channel'] == mock_channel

    @pytest.mark.asyncio
    async def test_log_taco_transaction_negative_count(self, taco_helper, mock_from_user, mock_to_user, entity_helper):
        mock_channel = MagicMock()
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        await taco_helper.log_taco_transaction(
            guild_id=999,
            toMember=mock_to_user,
            fromMember=mock_from_user,
            count=-3,
            total_tacos=7,
            reason="Penalty",
            type=tacotypes.TacoTypes.CUSTOM,
        )
        taco_helper.message_helper.send_embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_taco_transaction_singular_taco(self, taco_helper, mock_from_user, mock_to_user, entity_helper):
        mock_channel = MagicMock()
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        taco_helper.settings.get_string = MagicMock(
            side_effect=lambda gid, key, **kwargs: {
                "taco_singular": "taco",
                "taco_plural": "tacos",
                "tacos_log_action_received": "received",
            }.get(key, "default")
        )
        await taco_helper.log_taco_transaction(
            guild_id=999,
            toMember=mock_to_user,
            fromMember=mock_from_user,
            count=1,
            total_tacos=1,
            reason="First taco",
            type=tacotypes.TacoTypes.CUSTOM,
        )
        taco_helper.settings.get_string.assert_any_call(999, "taco_singular")

    @pytest.mark.asyncio
    async def test_log_taco_transaction_no_log_channel(self, taco_helper, mock_from_user, mock_to_user, entity_helper):
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)
        await taco_helper.log_taco_transaction(
            guild_id=999,
            toMember=mock_to_user,
            fromMember=mock_from_user,
            count=5,
            total_tacos=15,
            reason="Test",
            type=tacotypes.TacoTypes.CUSTOM,
        )
        taco_helper.message_helper.send_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_taco_transaction_exception_handling(
        self, taco_helper, mock_from_user, mock_to_user, entity_helper
    ):
        entity_helper.get_or_fetch_channel = AsyncMock(side_effect=Exception("Channel fetch failed"))
        await taco_helper.log_taco_transaction(
            guild_id=999,
            toMember=mock_to_user,
            fromMember=mock_from_user,
            count=5,
            total_tacos=15,
            reason="Test",
            type=tacotypes.TacoTypes.CUSTOM,
        )

    @pytest.mark.asyncio
    async def test_log_taco_purge_success(self, taco_helper, mock_from_user, mock_to_user, entity_helper):
        mock_channel = MagicMock()
        mock_channel.send = AsyncMock()
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=mock_channel)
        await taco_helper.log_taco_purge(
            guild_id=999, toMember=mock_to_user, fromMember=mock_from_user, reason="Violated rules"
        )
        mock_channel.send.assert_called_once()
        taco_helper.tacos_db.track_tacos_log.assert_called_once()
        call_kwargs = taco_helper.tacos_db.track_tacos_log.call_args.kwargs
        assert call_kwargs['count'] == 0
        assert call_kwargs['reason'] == "Violated rules"

    @pytest.mark.asyncio
    async def test_log_taco_purge_no_log_channel(self, taco_helper, mock_from_user, mock_to_user, entity_helper):
        entity_helper.get_or_fetch_channel = AsyncMock(return_value=None)
        await taco_helper.log_taco_purge(
            guild_id=999, toMember=mock_to_user, fromMember=mock_from_user, reason="Test purge"
        )
        taco_helper.tacos_db.track_tacos_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_taco_purge_exception_handling(self, taco_helper, mock_from_user, mock_to_user, entity_helper):
        entity_helper.get_or_fetch_channel = AsyncMock(side_effect=Exception("Channel error"))
        await taco_helper.log_taco_purge(guild_id=999, toMember=mock_to_user, fromMember=mock_from_user, reason="Test")
