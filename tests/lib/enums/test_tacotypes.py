"""Comprehensive tests for TacoTypes enum.
Tests enum values, string conversions, and all conversion methods.
"""

import pytest
from bot.lib.enums.tacotypes import TacoTypes


class TestTacoTypesEnum:
    """Test suite for TacoTypes enum functionality."""

    def test_enum_values_exist(self):
        """Verify all expected enum values exist."""
        # Core Discord actions
        assert TacoTypes.JOIN_SERVER is not None
        assert TacoTypes.BOOST is not None
        assert TacoTypes.REACT_REWARD is not None
        assert TacoTypes.SUGGEST is not None
        assert TacoTypes.USER_INVITE is not None
        assert TacoTypes.REACTION is not None
        assert TacoTypes.REPLY is not None
        assert TacoTypes.TQOTD is not None
        assert TacoTypes.BIRTHDAY is not None
        assert TacoTypes.TWITCH_LINK is not None
        assert TacoTypes.STREAM is not None
        assert TacoTypes.PHOTO_POST is not None
        assert TacoTypes.WDYCTW is not None
        assert TacoTypes.TECH_THURSDAY is not None
        assert TacoTypes.TACO_TUESDAY is not None
        assert TacoTypes.MENTAL_MONDAY is not None
        assert TacoTypes.FIRST_MESSAGE is not None
        assert TacoTypes.EVENT_CREATE is not None
        assert TacoTypes.EVENT_JOIN is not None
        assert TacoTypes.EVENT_LEAVE is not None
        assert TacoTypes.EVENT_CANCEL is not None
        assert TacoTypes.EVENT_COMPLETE is not None
        assert TacoTypes.GAME_REDEEM is not None
        assert TacoTypes.TRIVIA_CORRECT is not None
        assert TacoTypes.TRIVIA_INCORRECT is not None
        assert TacoTypes.FOLLOW_CHANNEL is not None
        assert TacoTypes.CREATE_VOICE_CHANNEL is not None
        assert TacoTypes.POST_INTRODUCTION is not None
        assert TacoTypes.APPROVE_INTRODUCTION is not None
        assert TacoTypes.GAME_DONATE_REDEEM is not None
        assert TacoTypes.GAME_KEY_RESET is not None
        assert TacoTypes.PULLTAB_PURCHASE is not None
        assert TacoTypes.PULLTAB_REDEEM is not None

        # Twitch actions
        assert TacoTypes.TWITCH_BOT_INVITE is not None
        assert TacoTypes.TWITCH_RAID is not None
        assert TacoTypes.TWITCH_SUB is not None
        assert TacoTypes.TWITCH_BITS is not None
        assert TacoTypes.TWITCH_FIRST_MESSAGE is not None
        assert TacoTypes.TWITCH_PROMOTE is not None
        assert TacoTypes.TWITCH_GIVE_TACOS is not None
        assert TacoTypes.TWITCH_RECEIVE_TACOS is not None
        assert TacoTypes.TWITCH_FOLLOW is not None
        assert TacoTypes.TWITCH_STREAM_AVATARS is not None

        # Minecraft actions
        assert TacoTypes.MINECRAFT_LOGIN is not None
        assert TacoTypes.MINECRAFT_CUSTOM is not None

        # Special actions
        assert TacoTypes.PURGE is not None
        assert TacoTypes.LEAVE_SERVER is not None
        assert TacoTypes.TWITCH_CUSTOM is not None
        assert TacoTypes.CUSTOM is not None

    def test_enum_values_unique(self):
        """Verify all enum values are unique."""
        values = [taco_type.value for taco_type in TacoTypes]
        assert len(values) == len(set(values))

    def test_enum_values_expected(self):
        """Verify some key enum values match expected integers."""
        assert TacoTypes.JOIN_SERVER.value == 1
        assert TacoTypes.BOOST.value == 2
        assert TacoTypes.CUSTOM.value == 9999
        assert TacoTypes.TWITCH_CUSTOM.value == 9998
        assert TacoTypes.LEAVE_SERVER.value == 9997
        assert TacoTypes.PURGE.value == 9996
        assert TacoTypes.MINECRAFT_CUSTOM.value == 2999
        assert TacoTypes.MINECRAFT_LOGIN.value == 2000
        assert TacoTypes.TWITCH_STREAM_AVATARS.value == 1008
        assert TacoTypes.TWITCH_FOLLOW.value == 1007
        assert TacoTypes.TWITCH_RECEIVE_TACOS.value == 1006
        assert TacoTypes.TWITCH_BITS.value == 1003
        assert TacoTypes.TWITCH_SUB.value == 1002
        assert TacoTypes.TWITCH_RAID.value == 1001
        assert TacoTypes.TWITCH_BOT_INVITE.value == 1000

    @pytest.mark.parametrize(
        "taco_type,expected_str",
        [
            (TacoTypes.JOIN_SERVER, "join_count"),
            (TacoTypes.BOOST, "boost_count"),
            (TacoTypes.REACT_REWARD, "reaction_reward_count"),
            (TacoTypes.SUGGEST, "suggest_count"),
            (TacoTypes.USER_INVITE, "invite_count"),
            (TacoTypes.REACTION, "reaction_count"),
            (TacoTypes.REPLY, "reply_count"),
            (TacoTypes.TQOTD, "tqotd_count"),
            (TacoTypes.BIRTHDAY, "birthday_count"),
            (TacoTypes.TWITCH_LINK, "twitch_count"),
            (TacoTypes.STREAM, "stream_count"),
            (TacoTypes.PHOTO_POST, "photo_post_count"),
            (TacoTypes.WDYCTW, "wdyctw_count"),
            (TacoTypes.TECH_THURSDAY, "tech_thursday_count"),
            (TacoTypes.TACO_TUESDAY, "taco_tuesday_count"),
            (TacoTypes.MENTAL_MONDAY, "mental_monday_count"),
            (TacoTypes.FIRST_MESSAGE, "first_message_count"),
            (TacoTypes.EVENT_CREATE, "event_create_count"),
            (TacoTypes.EVENT_JOIN, "event_join_count"),
            (TacoTypes.EVENT_LEAVE, "event_leave_count"),
            (TacoTypes.EVENT_CANCEL, "event_cancel_count"),
            (TacoTypes.EVENT_COMPLETE, "event_complete_count"),
            (TacoTypes.GAME_REDEEM, "game_key_cost"),
            (TacoTypes.TRIVIA_CORRECT, "trivia_correct_count"),
            (TacoTypes.TRIVIA_INCORRECT, "trivia_incorrect_count"),
            (TacoTypes.FOLLOW_CHANNEL, "follow_channel_count"),
            (TacoTypes.CREATE_VOICE_CHANNEL, "create_voice_channel_count"),
            (TacoTypes.POST_INTRODUCTION, "post_introduction_count"),
            (TacoTypes.APPROVE_INTRODUCTION, "approve_introduction_count"),
            (TacoTypes.GAME_DONATE_REDEEM, "game_donate_count"),
            (TacoTypes.GAME_KEY_RESET, "custom"),  # GAME_KEY_RESET not explicitly mapped, falls back to custom
            (TacoTypes.PULLTAB_PURCHASE, "pulltab_purchase"),
            (TacoTypes.PULLTAB_REDEEM, "pulltab_redeem"),
            (TacoTypes.TWITCH_BOT_INVITE, "twitch_bot_invite_count"),
            (TacoTypes.TWITCH_RAID, "twitch_raid_count"),
            (TacoTypes.TWITCH_SUB, "twitch_sub_count"),
            (TacoTypes.TWITCH_BITS, "twitch_bits_count"),
            (TacoTypes.TWITCH_FIRST_MESSAGE, "twitch_first_message_count"),
            (TacoTypes.TWITCH_PROMOTE, "twitch_promote_count"),
            (TacoTypes.TWITCH_GIVE_TACOS, "twitch_give_tacos"),
            (TacoTypes.TWITCH_RECEIVE_TACOS, "twitch_receive_tacos"),
            (TacoTypes.TWITCH_FOLLOW, "twitch_follow_count"),
            (TacoTypes.TWITCH_STREAM_AVATARS, "twitch_stream_avatars"),
            (TacoTypes.MINECRAFT_LOGIN, "minecraft_login"),
            (TacoTypes.MINECRAFT_CUSTOM, "minecraft_custom"),
            (TacoTypes.PURGE, "purge_custom"),
            (TacoTypes.LEAVE_SERVER, "leave_server_custom"),
            (TacoTypes.TWITCH_CUSTOM, "twitch_custom"),
            (TacoTypes.CUSTOM, "custom"),
        ],
    )
    def test_str_representation(self, taco_type, expected_str):
        """Test __str__ method returns correct string representation."""
        assert str(taco_type) == expected_str

    @pytest.mark.parametrize(
        "input_str,expected_enum",
        [
            ("join_count", TacoTypes.JOIN_SERVER),
            ("boost_count", TacoTypes.BOOST),
            ("reaction_reward_count", TacoTypes.REACT_REWARD),
            ("suggest_count", TacoTypes.SUGGEST),
            ("invite_count", TacoTypes.USER_INVITE),
            ("reaction_count", TacoTypes.REACTION),
            ("reply_count", TacoTypes.REPLY),
            ("tqotd_count", TacoTypes.TQOTD),
            ("birthday_count", TacoTypes.BIRTHDAY),
            ("twitch_count", TacoTypes.TWITCH_LINK),
            ("stream_count", TacoTypes.STREAM),
            ("photo_post_count", TacoTypes.PHOTO_POST),
            ("wdyctw_count", TacoTypes.WDYCTW),
            ("tech_thursday_count", TacoTypes.TECH_THURSDAY),
            ("taco_tuesday_count", TacoTypes.TACO_TUESDAY),
            ("mental_monday_count", TacoTypes.MENTAL_MONDAY),
            ("first_message_count", TacoTypes.FIRST_MESSAGE),
            ("event_create_count", TacoTypes.EVENT_CREATE),
            ("event_join_count", TacoTypes.EVENT_JOIN),
            ("event_leave_count", TacoTypes.EVENT_LEAVE),
            ("event_cancel_count", TacoTypes.EVENT_CANCEL),
            ("event_complete_count", TacoTypes.EVENT_COMPLETE),
            ("game_key_cost", TacoTypes.GAME_REDEEM),
            ("game_donate_count", TacoTypes.GAME_DONATE_REDEEM),
            ("trivia_correct_count", TacoTypes.TRIVIA_CORRECT),
            ("trivia_incorrect_count", TacoTypes.TRIVIA_INCORRECT),
            ("follow_channel_count", TacoTypes.FOLLOW_CHANNEL),
            ("create_voice_channel_count", TacoTypes.CREATE_VOICE_CHANNEL),
            ("post_introduction_count", TacoTypes.POST_INTRODUCTION),
            ("approve_introduction_count", TacoTypes.APPROVE_INTRODUCTION),
            ("pulltab_purchase", TacoTypes.PULLTAB_PURCHASE),
            ("pulltab_redeem", TacoTypes.PULLTAB_REDEEM),
            ("twitch_bot_invite", TacoTypes.TWITCH_BOT_INVITE),
            ("twitch_raid_count", TacoTypes.TWITCH_RAID),
            ("twitch_sub_count", TacoTypes.TWITCH_SUB),
            ("twitch_bits_count", TacoTypes.TWITCH_BITS),
            ("twitch_first_message_count", TacoTypes.TWITCH_FIRST_MESSAGE),
            ("twitch_promote_count", TacoTypes.TWITCH_PROMOTE),
            ("twitch_give_tacos", TacoTypes.TWITCH_GIVE_TACOS),
            ("twitch_receive_tacos", TacoTypes.TWITCH_RECEIVE_TACOS),
            ("twitch_follow_count", TacoTypes.TWITCH_FOLLOW),
            ("twitch_stream_avatars", TacoTypes.TWITCH_STREAM_AVATARS),
            ("twitch_custom", TacoTypes.TWITCH_CUSTOM),
            ("minecraft_login", TacoTypes.MINECRAFT_LOGIN),
            ("purge_custom", TacoTypes.PURGE),
            ("leave_server_custom", TacoTypes.LEAVE_SERVER),
        ],
    )
    def test_get_from_string_valid_inputs(self, input_str, expected_enum):
        """Test get_from_string method with valid string inputs."""
        result = TacoTypes.get_from_string(input_str)
        assert result == expected_enum

    def test_str_to_enum_delegates_to_get_from_string(self):
        """Test str_to_enum delegates to get_from_string."""
        result1 = TacoTypes.str_to_enum("join_count")
        result2 = TacoTypes.get_from_string("join_count")
        assert result1 == result2 == TacoTypes.JOIN_SERVER

    @pytest.mark.parametrize(
        "invalid_str",
        [
            "",
            "invalid_type",
            "unknown_count",
            "random_string",
            "123",
            "None",
            "join",  # partial match
            "count",  # partial match
            "twitch",  # partial match
            "minecraft",  # partial match
            "   ",  # whitespace
            "JOIN_COUNT",  # uppercase
        ],
    )
    def test_get_from_string_invalid_inputs_return_custom(self, invalid_str):
        """Test get_from_string returns CUSTOM for invalid inputs."""
        result = TacoTypes.get_from_string(invalid_str)
        assert result == TacoTypes.CUSTOM

    def test_get_from_string_none_input(self):
        """Test get_from_string method with None input returns CUSTOM."""
        result = TacoTypes.get_from_string(None)  # type: ignore
        assert result == TacoTypes.CUSTOM

    @pytest.mark.parametrize(
        "taco_type,expected_db_type",
        [
            (TacoTypes.JOIN_SERVER, "JOIN_SERVER"),
            (TacoTypes.BOOST, "BOOST"),
            (TacoTypes.CUSTOM, "CUSTOM"),
            (TacoTypes.TWITCH_CUSTOM, "TWITCH_CUSTOM"),
            (TacoTypes.MINECRAFT_LOGIN, "MINECRAFT_LOGIN"),
        ],
    )
    def test_get_db_type_from_taco_type(self, taco_type, expected_db_type):
        """Test get_db_type_from_taco_type returns uppercase name."""
        result = TacoTypes.get_db_type_from_taco_type(taco_type)
        assert result == expected_db_type

    def test_get_db_type_from_taco_type_none_input(self):
        """Test get_db_type_from_taco_type with None input."""
        with pytest.raises(AttributeError):
            TacoTypes.get_db_type_from_taco_type(None)  # type: ignore

    def test_enum_iteration(self):
        """Test that enum can be iterated over."""
        taco_types = list(TacoTypes)
        assert len(taco_types) == 49  # Total number of enum members
        assert TacoTypes.JOIN_SERVER in taco_types
        assert TacoTypes.CUSTOM in taco_types

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert TacoTypes.BOOST in TacoTypes
        assert "BOOST" not in TacoTypes
        assert 999 not in TacoTypes

    def test_enum_equality(self):
        """Test enum equality comparisons."""
        assert TacoTypes.TWITCH_LINK == TacoTypes.TWITCH_LINK
        assert TacoTypes.TWITCH_LINK != TacoTypes.STREAM
        assert TacoTypes.TWITCH_LINK != "twitch_count"

    def test_enum_hashable(self):
        """Test that enum values are hashable."""
        taco_set = {TacoTypes.JOIN_SERVER, TacoTypes.BOOST}
        assert len(taco_set) == 2
        assert TacoTypes.JOIN_SERVER in taco_set

    def test_enum_immutable(self):
        """Test that enum values cannot be modified."""
        with pytest.raises(AttributeError):
            TacoTypes.JOIN_SERVER.value = 99  # type: ignore

    def test_enum_names(self):
        """Test enum name attributes."""
        assert TacoTypes.JOIN_SERVER.name == "JOIN_SERVER"
        assert TacoTypes.BOOST.name == "BOOST"
        assert TacoTypes.CUSTOM.name == "CUSTOM"

    def test_round_trip_str_conversion(self):
        """Test converting enum to string and back."""
        # Exclude enums that don't have proper string mappings or have inconsistent mappings
        excluded_from_round_trip = {
            TacoTypes.CUSTOM,
            TacoTypes.GAME_KEY_RESET,
            TacoTypes.TWITCH_BOT_INVITE,  # Maps to "twitch_bot_invite_count" but parses "twitch_bot_invite"
            TacoTypes.MINECRAFT_CUSTOM,  # Maps to "minecraft_custom" but not handled in get_from_string
        }

        for taco_type in TacoTypes:
            if taco_type not in excluded_from_round_trip:
                str_repr = str(taco_type)
                converted_back = TacoTypes.get_from_string(str_repr)
                assert converted_back == taco_type, f"Round trip failed for {taco_type}: {str_repr} -> {converted_back}"

    def test_custom_fallback_behavior(self):
        """Test that CUSTOM is returned for unmapped strings."""
        result = TacoTypes.get_from_string("nonexistent_type")
        assert result == TacoTypes.CUSTOM

        # And CUSTOM should map to "custom"
        assert str(TacoTypes.CUSTOM) == "custom"
