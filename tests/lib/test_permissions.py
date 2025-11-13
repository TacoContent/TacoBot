"""Comprehensive tests for Permissions class.
Tests all permission checking methods with mocked dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from bot.lib.enums.permissions import TacoPermissions
from bot.lib.permissions import Permissions


class TestPermissionsInit:
    """Test Permissions class initialization."""

    def test_init_with_no_parameters(self):
        """Test initialization with no parameters uses defaults."""
        with (
            patch("bot.lib.permissions.Settings") as mock_settings_class,
            patch("bot.lib.permissions.PermissionsDatabase") as mock_db_class,
            patch("bot.lib.permissions.EntityHelper") as mock_helper_class,
        ):
            mock_bot = MagicMock()

            _perms = Permissions(mock_bot)

            # Verify defaults were instantiated
            mock_settings_class.assert_called_once()
            mock_db_class.assert_called_once()
            mock_helper_class.assert_called_once_with(mock_bot)

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters provided."""
        mock_bot = MagicMock()
        mock_settings = MagicMock()
        mock_db = MagicMock()
        mock_helper = MagicMock()

        perms = Permissions(bot=mock_bot, settings=mock_settings, permissions_db=mock_db, entity_helper=mock_helper)

        # Verify provided instances are used
        assert perms.settings is mock_settings
        assert perms.permissions_db is mock_db
        assert perms.entity_helper is mock_helper

    def test_init_with_partial_parameters(self):
        """Test initialization with some parameters provided."""
        with (
            patch("bot.lib.permissions.Settings") as mock_settings_class,
            patch("bot.lib.permissions.EntityHelper") as mock_helper_class,
        ):
            mock_bot = MagicMock()
            mock_db = MagicMock()

            perms = Permissions(bot=mock_bot, permissions_db=mock_db)

            # Verify provided instance is used
            assert perms.permissions_db is mock_db

            # Verify defaults were instantiated for others
            mock_settings_class.assert_called_once()
            mock_helper_class.assert_called_once_with(mock_bot)


class TestHasTacoPermission:
    """Test has_taco_permission method."""

    @pytest.fixture
    def setup(self):
        """Setup common test dependencies."""
        self.mock_bot = MagicMock()
        self.mock_settings = MagicMock()
        self.mock_db = MagicMock()
        self.mock_helper = MagicMock()

        self.perms = Permissions(
            bot=self.mock_bot, settings=self.mock_settings, permissions_db=self.mock_db, entity_helper=self.mock_helper
        )

    def test_with_discord_member_and_enum_permission(self, setup):
        """Test with discord.Member and TacoPermissions enum."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345

        self.mock_db.has_user_permission.return_value = True

        result = self.perms.has_taco_permission(
            guild_id=999, user=mock_member, permission=TacoPermissions.TACOS_NO_GIVE
        )

        assert result is True
        self.mock_db.has_user_permission.assert_called_once_with(999, 12345, TacoPermissions.TACOS_NO_GIVE)

    def test_with_discord_user_and_enum_permission(self, setup):
        """Test with discord.User and TacoPermissions enum."""
        mock_user = MagicMock(spec=discord.User)
        mock_user.id = 67890

        self.mock_db.has_user_permission.return_value = False

        result = self.perms.has_taco_permission(
            guild_id=111, user=mock_user, permission=TacoPermissions.CLAIM_GAME_DISABLED
        )

        assert result is False
        self.mock_db.has_user_permission.assert_called_once_with(111, 67890, TacoPermissions.CLAIM_GAME_DISABLED)

    def test_with_user_id_integer_and_enum_permission(self, setup):
        """Test with user as integer ID and TacoPermissions enum."""
        self.mock_db.has_user_permission.return_value = True

        result = self.perms.has_taco_permission(guild_id=222, user=55555, permission=TacoPermissions.TACOS_NO_RECEIVE)

        assert result is True
        self.mock_db.has_user_permission.assert_called_once_with(222, 55555, TacoPermissions.TACOS_NO_RECEIVE)

    def test_with_string_permission(self, setup):
        """Test with permission as string (should convert to enum)."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345

        self.mock_db.has_user_permission.return_value = True

        with patch("bot.lib.permissions.TacoPermissions.from_str") as mock_from_str:
            mock_from_str.return_value = TacoPermissions.TACOS_NO_GIVE

            result = self.perms.has_taco_permission(guild_id=333, user=mock_member, permission="tacos_no_give")

            assert result is True
            mock_from_str.assert_called_once_with("tacos_no_give")
            self.mock_db.has_user_permission.assert_called_once_with(333, 12345, TacoPermissions.TACOS_NO_GIVE)

    def test_with_list_of_enum_permissions_any_match(self, setup):
        """Test with list of permissions - returns True if any match."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345

        # First permission returns False, second returns True
        self.mock_db.has_user_permission.side_effect = [False, True]

        result = self.perms.has_taco_permission(
            guild_id=444, user=mock_member, permission=[TacoPermissions.TACOS_NO_GIVE, TacoPermissions.TACOS_NO_RECEIVE]
        )

        assert result is True
        assert self.mock_db.has_user_permission.call_count == 2

    def test_with_list_of_enum_permissions_no_match(self, setup):
        """Test with list of permissions - returns False if none match."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345

        # All permissions return False
        self.mock_db.has_user_permission.return_value = False

        result = self.perms.has_taco_permission(
            guild_id=555, user=mock_member, permission=[TacoPermissions.TACOS_NO_GIVE, TacoPermissions.TACOS_NO_RECEIVE]
        )

        assert result is False

    def test_with_list_of_string_permissions(self, setup):
        """Test with list of string permissions (should convert each to enum)."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345

        self.mock_db.has_user_permission.side_effect = [False, True]

        with patch("bot.lib.permissions.TacoPermissions.from_str") as mock_from_str:
            mock_from_str.side_effect = [TacoPermissions.TACOS_NO_GIVE, TacoPermissions.TACOS_NO_RECEIVE]

            result = self.perms.has_taco_permission(
                guild_id=666, user=mock_member, permission=["tacos_no_give", "tacos_no_receive"]
            )

            assert result is True
            assert mock_from_str.call_count == 2

    def test_with_mixed_list_of_enum_and_string_permissions(self, setup):
        """Test with list containing both enums and strings."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345

        self.mock_db.has_user_permission.side_effect = [False, True]

        with patch("bot.lib.permissions.TacoPermissions.from_str") as mock_from_str:
            mock_from_str.return_value = TacoPermissions.TACOS_NO_RECEIVE

            result = self.perms.has_taco_permission(
                guild_id=777, user=mock_member, permission=[TacoPermissions.TACOS_NO_GIVE, "tacos_no_receive"]
            )

            assert result is True
            mock_from_str.assert_called_once_with("tacos_no_receive")

    def test_with_none_permissions_db(self, setup):
        """Test with None permissions_db returns False."""
        self.perms.permissions_db = None  # type: ignore
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345

        result = self.perms.has_taco_permission(
            guild_id=888, user=mock_member, permission=TacoPermissions.TACOS_NO_GIVE
        )

        assert result is False

    def test_with_empty_permission_list(self, setup):
        """Test with empty permission list."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345

        result = self.perms.has_taco_permission(guild_id=999, user=mock_member, permission=[])

        # any() returns False for empty iterable
        assert result is False


@pytest.mark.asyncio
class TestHasPermission:
    """Test has_permission method (async)."""

    @pytest.fixture
    def setup(self):
        """Setup common test dependencies."""
        self.mock_bot = MagicMock()
        self.mock_settings = MagicMock()
        self.mock_db = MagicMock()
        self.mock_helper = MagicMock()

        self.perms = Permissions(
            bot=self.mock_bot, settings=self.mock_settings, permissions_db=self.mock_db, entity_helper=self.mock_helper
        )

    async def test_with_none_user_returns_false(self, setup):
        """Test with None user returns False."""
        result = await self.perms.has_permission(user=None)
        assert result is False

    async def test_with_discord_member_and_no_permissions(self, setup):
        """Test with discord.Member and no permissions check (should return True)."""
        mock_member = MagicMock(spec=discord.Member)

        result = await self.perms.has_permission(user=mock_member, permissions=None)

        assert result is True

    async def test_with_discord_member_and_matching_permissions(self, setup):
        """Test with discord.Member having required permissions."""
        mock_member = MagicMock(spec=discord.Member)
        mock_perms = discord.Permissions(administrator=True, manage_guild=True)
        mock_member.guild_permissions = discord.Permissions(administrator=True, manage_guild=True, manage_roles=True)

        result = await self.perms.has_permission(user=mock_member, permissions=mock_perms)

        # guild_permissions >= required permissions
        assert result is True

    async def test_with_discord_member_and_insufficient_permissions(self, setup):
        """Test with discord.Member lacking required permissions."""
        mock_member = MagicMock(spec=discord.Member)
        mock_perms = discord.Permissions(administrator=True)
        mock_member.guild_permissions = discord.Permissions(manage_guild=True)

        result = await self.perms.has_permission(user=mock_member, permissions=mock_perms)

        assert result is False

    async def test_with_user_id_and_guild_id(self, setup):
        """Test with user ID and guild ID (should fetch member)."""
        self.mock_helper.get_or_fetch_member = AsyncMock()
        mock_member = MagicMock(spec=discord.Member)
        mock_member.guild_permissions = discord.Permissions(administrator=True)
        self.mock_helper.get_or_fetch_member.return_value = mock_member

        required_perms = discord.Permissions(administrator=True)
        result = await self.perms.has_permission(user=12345, guildId=999, permissions=required_perms)

        assert result is True
        self.mock_helper.get_or_fetch_member.assert_called_once_with(999, 12345)

    async def test_with_user_id_but_no_guild_id_raises_error(self, setup):
        """Test with user ID but no guild ID raises ValueError."""
        with pytest.raises(ValueError, match="guildId must be specified"):
            await self.perms.has_permission(user=12345, permissions=discord.Permissions(administrator=True))

    async def test_with_user_id_but_member_not_found(self, setup):
        """Test with user ID but member not found returns False."""
        self.mock_helper.get_or_fetch_member = AsyncMock(return_value=None)

        result = await self.perms.has_permission(
            user=12345, guildId=999, permissions=discord.Permissions(administrator=True)
        )

        assert result is False

    async def test_with_invalid_user_type(self, setup):
        """Test with invalid user type returns False."""
        result = await self.perms.has_permission(user="invalid_type", permissions=discord.Permissions(administrator=True))  # type: ignore

        assert result is False


@pytest.mark.asyncio
class TestHasRole:
    """Test has_role method (async)."""

    @pytest.fixture
    def setup(self):
        """Setup common test dependencies."""
        self.mock_bot = MagicMock()
        self.mock_settings = MagicMock()
        self.mock_db = MagicMock()
        self.mock_helper = MagicMock()

        self.perms = Permissions(
            bot=self.mock_bot, settings=self.mock_settings, permissions_db=self.mock_db, entity_helper=self.mock_helper
        )

    async def test_with_discord_member_and_role_id_has_role(self, setup):
        """Test with discord.Member having the specified role ID."""
        mock_role_1 = MagicMock(spec=discord.Role)
        mock_role_1.id = 111
        mock_role_2 = MagicMock(spec=discord.Role)
        mock_role_2.id = 222
        mock_role_3 = MagicMock(spec=discord.Role)
        mock_role_3.id = 333

        mock_member = MagicMock(spec=discord.Member)
        mock_member.roles = [mock_role_1, mock_role_2, mock_role_3]

        result = await self.perms.has_role(user=mock_member, role=222)

        assert result is True

    async def test_with_discord_member_and_role_id_no_role(self, setup):
        """Test with discord.Member not having the specified role ID."""
        mock_role_1 = MagicMock(spec=discord.Role)
        mock_role_1.id = 111

        mock_member = MagicMock(spec=discord.Member)
        mock_member.roles = [mock_role_1]

        result = await self.perms.has_role(user=mock_member, role=999)

        assert result is False

    async def test_with_discord_member_and_role_object(self, setup):
        """Test with discord.Member and discord.Role object."""
        mock_role_obj = MagicMock(spec=discord.Role)
        mock_role_obj.id = 555

        mock_role_in_member = MagicMock(spec=discord.Role)
        mock_role_in_member.id = 555

        mock_member = MagicMock(spec=discord.Member)
        mock_member.roles = [mock_role_in_member]

        result = await self.perms.has_role(user=mock_member, role=mock_role_obj)

        assert result is True

    async def test_with_user_id_and_guild_id(self, setup):
        """Test with user ID and guild ID (should fetch member)."""
        self.mock_helper.get_or_fetch_member = AsyncMock()

        mock_role = MagicMock(spec=discord.Role)
        mock_role.id = 777

        mock_member = MagicMock(spec=discord.Member)
        mock_member.roles = [mock_role]
        self.mock_helper.get_or_fetch_member.return_value = mock_member

        result = await self.perms.has_role(user=12345, guildId=999, role=777)

        assert result is True
        self.mock_helper.get_or_fetch_member.assert_called_once_with(999, 12345)

    async def test_with_user_id_but_no_guild_id_raises_error(self, setup):
        """Test with user ID but no guild ID raises ValueError."""
        with pytest.raises(ValueError, match="guildId must be specified"):
            await self.perms.has_role(user=12345, role=777)

    async def test_with_user_id_but_member_not_found(self, setup):
        """Test with user ID but member not found returns False."""
        self.mock_helper.get_or_fetch_member = AsyncMock(return_value=None)

        result = await self.perms.has_role(user=12345, guildId=999, role=777)

        assert result is False

    async def test_with_invalid_user_type_raises_error(self, setup):
        """Test with invalid user type raises ValueError."""
        with pytest.raises(ValueError, match="user must be an int or a discord.Member"):
            await self.perms.has_role(user="invalid_type", role=777)  # type: ignore

    async def test_with_none_role_raises_error(self, setup):
        """Test with None role raises ValueError."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.roles = []

        # Current implementation raises ValueError for None role
        with pytest.raises(ValueError, match="role must be an int or a discord.Role"):
            await self.perms.has_role(user=mock_member, role=None)

    async def test_with_invalid_role_type_raises_error(self, setup):
        """Test with invalid role type raises ValueError."""
        mock_member = MagicMock(spec=discord.Member)

        with pytest.raises(ValueError, match="role must be an int or a discord.Role"):
            await self.perms.has_role(user=mock_member, role="invalid_role")  # type: ignore

    async def test_with_empty_roles_list(self, setup):
        """Test with member having no roles."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.roles = []

        result = await self.perms.has_role(user=mock_member, role=123)

        assert result is False


@pytest.mark.asyncio
class TestIsAdmin:
    """Test is_admin method (async)."""

    @pytest.fixture
    def setup(self):
        """Setup common test dependencies."""
        self.mock_bot = MagicMock()
        self.mock_settings = MagicMock()
        self.mock_db = MagicMock()
        self.mock_helper = MagicMock()

        self.perms = Permissions(
            bot=self.mock_bot, settings=self.mock_settings, permissions_db=self.mock_db, entity_helper=self.mock_helper
        )

    async def test_with_discord_member_is_admin(self, setup):
        """Test with discord.Member having administrator permission."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.guild_permissions = discord.Permissions(administrator=True)

        result = await self.perms.is_admin(user=mock_member)

        assert result is True

    async def test_with_discord_member_not_admin(self, setup):
        """Test with discord.Member not having administrator permission."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.guild_permissions = discord.Permissions(manage_guild=True)

        result = await self.perms.is_admin(user=mock_member)

        assert result is False

    async def test_with_user_id_and_guild_id_is_admin(self, setup):
        """Test with user ID and guild ID (should fetch member who is admin)."""
        self.mock_helper.get_or_fetch_member = AsyncMock()

        mock_member = MagicMock(spec=discord.Member)
        mock_member.guild_permissions = discord.Permissions(administrator=True)
        self.mock_helper.get_or_fetch_member.return_value = mock_member

        result = await self.perms.is_admin(user=12345, guildId=999)

        assert result is True
        self.mock_helper.get_or_fetch_member.assert_called_once_with(999, 12345)

    async def test_with_user_id_but_no_guild_id_raises_error(self, setup):
        """Test with user ID but no guild ID raises ValueError."""
        with pytest.raises(ValueError, match="guildId must be specified"):
            await self.perms.is_admin(user=12345)

    async def test_with_user_id_but_member_not_found(self, setup):
        """Test with user ID but member not found."""
        self.mock_helper.get_or_fetch_member = AsyncMock(return_value=None)

        # This will call has_permission with None member, which returns False
        result = await self.perms.is_admin(user=12345, guildId=999)

        assert result is False

    async def test_with_invalid_user_type_raises_error(self, setup):
        """Test with invalid user type raises ValueError."""
        with pytest.raises(ValueError, match="user must be an int or a discord.Member"):
            await self.perms.is_admin(user="invalid_type")  # type: ignore

    async def test_delegates_to_has_permission(self, setup):
        """Test is_admin delegates to has_permission with admin permissions."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.guild_permissions = discord.Permissions(administrator=True)

        # Patch has_permission to verify it's called correctly
        with patch.object(self.perms, "has_permission", new_callable=AsyncMock) as mock_has_perm:
            mock_has_perm.return_value = True

            result = await self.perms.is_admin(user=mock_member)

            assert result is True
            # Verify has_permission was called with admin permissions
            call_args = mock_has_perm.call_args
            assert call_args[0][0] == mock_member  # member argument
            assert call_args[0][1].administrator is True  # permissions argument


class TestPermissionsEdgeCases:
    """Edge cases and integration scenarios for Permissions class."""

    @pytest.fixture
    def setup(self):
        """Setup common test dependencies."""
        self.mock_bot = MagicMock()
        self.mock_settings = MagicMock()
        self.mock_db = MagicMock()
        self.mock_helper = MagicMock()

        self.perms = Permissions(
            bot=self.mock_bot, settings=self.mock_settings, permissions_db=self.mock_db, entity_helper=self.mock_helper
        )

    def test_has_taco_permission_with_all_permissions_false(self, setup):
        """Test checking multiple permissions when all are false."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345
        self.mock_db.has_user_permission.return_value = False

        perms_to_check = [
            TacoPermissions.TACOS_NO_GIVE,
            TacoPermissions.TACOS_NO_RECEIVE,
            TacoPermissions.CLAIM_GAME_DISABLED,
        ]

        result = self.perms.has_taco_permission(
            guild_id=999, user=mock_member, permission=perms_to_check  # type: ignore
        )
        assert result is False
        # any() short-circuits, but if all are False, all will be checked
        assert self.mock_db.has_user_permission.call_count == 3

    def test_has_taco_permission_short_circuits_on_first_true(self, setup):
        """Test that checking multiple permissions short-circuits on first True."""
        mock_member = MagicMock(spec=discord.Member)
        mock_member.id = 12345

        # First one is True
        self.mock_db.has_user_permission.side_effect = [True, False, False]

        perms_to_check = [
            TacoPermissions.TACOS_NO_GIVE,
            TacoPermissions.TACOS_NO_RECEIVE,
            TacoPermissions.CLAIM_GAME_DISABLED,
        ]

        result = self.perms.has_taco_permission(
            guild_id=999, user=mock_member, permission=perms_to_check  # type: ignore
        )

        assert result is True
        # Should only check until first True (any() short-circuits)
        assert self.mock_db.has_user_permission.call_count == 1

    @pytest.mark.asyncio
    async def test_has_permission_with_exact_matching_permissions(self, setup):
        """Test with permissions that exactly match (edge case of >=)."""
        mock_member = MagicMock(spec=discord.Member)
        required_perms = discord.Permissions(administrator=True, manage_guild=True)
        mock_member.guild_permissions = discord.Permissions(administrator=True, manage_guild=True)

        result = await self.perms.has_permission(user=mock_member, permissions=required_perms)

        assert result is True

    @pytest.mark.asyncio
    async def test_has_role_with_multiple_roles_checks_all(self, setup):
        """Test with member having multiple roles, checking if specific one exists."""
        roles = [MagicMock(spec=discord.Role) for _ in range(5)]
        for i, role in enumerate(roles):
            role.id = 100 + i

        mock_member = MagicMock(spec=discord.Member)
        mock_member.roles = roles

        # Check for role in the middle
        result = await self.perms.has_role(user=mock_member, role=102)

        assert result is True
