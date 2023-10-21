### NOTE: UPDATE THIS FILE WHEN CHANGING TACO TYPES ###
### UPDATE TacoBot/cogs/lib/tacotypes.py WHEN CHANGING TACO TYPES ###
### UPDATE TacoBotTwitch/cogs/lib/tacotypes.py WHEN CHANGING TACO TYPES ###

from enum import Enum


class TacoTypes(Enum):
    JOIN_SERVER = 1
    BOOST = 2
    REACT_REWARD = 3
    SUGGEST = 4
    USER_INVITE = 5
    REACTION = 6
    REPLY = 7
    TQOTD = 8
    BIRTHDAY = 9
    TWITCH_LINK = 10
    STREAM = 11
    PHOTO_POST = 12
    WDYCTW = 13
    TECH_THURSDAY = 14
    TACO_TUESDAY = 15
    MENTAL_MONDAY = 16
    FIRST_MESSAGE = 17
    EVENT_CREATE = 18
    EVENT_JOIN = 19
    EVENT_LEAVE = 20
    EVENT_CANCEL = 21
    EVENT_COMPLETE = 22
    GAME_REDEEM = 23
    TRIVIA_CORRECT = 24
    TRIVIA_INCORRECT = 25
    FOLLOW_CHANNEL = 26
    CREATE_VOICE_CHANNEL = 27
    POST_INTRODUCTION = 28
    APPROVE_INTRODUCTION = 29
    GAME_DONATE_REDEEM = 30

    TWITCH_BOT_INVITE = 1000  # Invite @OurTacoBot to your Twitch channel
    TWITCH_RAID = 1001
    TWITCH_SUB = 1002
    TWITCH_BITS = 1003
    TWITCH_FIRST_MESSAGE = 1004
    TWITCH_PROMOTE = 1005
    TWITCH_GIVE_TACOS = 32
    TWITCH_RECEIVE_TACOS = 1006
    TWITCH_FOLLOW = 1007  # not yet implemented until i can figure out how to get the event from eventsub

    TWITCH_STREAM_AVATARS = 1008
    PURGE = 9996
    LEAVE_SERVER = 9997

    TWITCH_CUSTOM = 9998
    CUSTOM = 9999

    @staticmethod
    def get_from_string(taco_type_string):
        if taco_type_string == "join_count":
            return TacoTypes.JOIN_SERVER
        elif taco_type_string == "boost_count":
            return TacoTypes.BOOST
        elif taco_type_string == "reaction_reward_count":
            return TacoTypes.REACT_REWARD
        elif taco_type_string == "suggest_count":
            return TacoTypes.SUGGEST
        elif taco_type_string == "invite_count":
            return TacoTypes.USER_INVITE
        elif taco_type_string == "reaction_count":
            return TacoTypes.REACTION
        elif taco_type_string == "reply_count":
            return TacoTypes.REPLY
        elif taco_type_string == "tqotd_count":
            return TacoTypes.TQOTD
        elif taco_type_string == "birthday_count":
            return TacoTypes.BIRTHDAY
        elif taco_type_string == "twitch_count":
            return TacoTypes.TWITCH_LINK
        elif taco_type_string == "stream_count":
            return TacoTypes.STREAM
        elif taco_type_string == "photo_post_count":
            return TacoTypes.PHOTO_POST
        elif taco_type_string == "wdyctw_count":
            return TacoTypes.WDYCTW
        elif taco_type_string == "tech_thursday_count":
            return TacoTypes.TECH_THURSDAY
        elif taco_type_string == "taco_tuesday_count":
            return TacoTypes.TACO_TUESDAY
        elif taco_type_string == "mental_monday_count":
            return TacoTypes.MENTAL_MONDAY
        elif taco_type_string == "first_message_count":
            return TacoTypes.FIRST_MESSAGE
        elif taco_type_string == "event_create_count":
            return TacoTypes.EVENT_CREATE
        elif taco_type_string == "event_join_count":
            return TacoTypes.EVENT_JOIN
        elif taco_type_string == "event_leave_count":
            return TacoTypes.EVENT_LEAVE
        elif taco_type_string == "event_cancel_count":
            return TacoTypes.EVENT_CANCEL
        elif taco_type_string == "event_complete_count":
            return TacoTypes.EVENT_COMPLETE
        elif taco_type_string == "purge_custom":
            return TacoTypes.PURGE
        elif taco_type_string == "leave_server_custom":
            return TacoTypes.LEAVE_SERVER
        elif taco_type_string == "game_key_cost":
            return TacoTypes.GAME_REDEEM
        elif taco_type_string == "game_donate_count":
            return TacoTypes.GAME_DONATE_REDEEM
        elif taco_type_string == "trivia_correct_count":
            return TacoTypes.TRIVIA_CORRECT
        elif taco_type_string == "trivia_incorrect_count":
            return TacoTypes.TRIVIA_INCORRECT
        elif taco_type_string == "follow_channel_count":
            # this can't be triggered by events
            return TacoTypes.FOLLOW_CHANNEL
        elif taco_type_string == "create_voice_channel_count":
            return TacoTypes.CREATE_VOICE_CHANNEL
        elif taco_type_string == "post_introduction_count":
            return TacoTypes.POST_INTRODUCTION
        elif taco_type_string == "approve_introduction_count":
            return TacoTypes.APPROVE_INTRODUCTION
        elif taco_type_string == "twitch_bot_invite":
            return TacoTypes.TWITCH_BOT_INVITE
        elif taco_type_string == "twitch_raid_count":
            return TacoTypes.TWITCH_RAID
        elif taco_type_string == "twitch_sub_count":
            return TacoTypes.TWITCH_SUB
        elif taco_type_string == "twitch_bits_count":
            return TacoTypes.TWITCH_BITS
        elif taco_type_string == "twitch_first_message_count":
            return TacoTypes.TWITCH_FIRST_MESSAGE
        elif taco_type_string == "twitch_promote_count":
            return TacoTypes.TWITCH_PROMOTE
        elif taco_type_string == "twitch_give_tacos":
            # this property is not saved in settings, as it should be the amount they give
            return TacoTypes.TWITCH_GIVE_TACOS
        elif taco_type_string == "twitch_receive_tacos":
            # this property is not saved in settings, as it should be the amount they receive
            return TacoTypes.TWITCH_RECEIVE_TACOS
        elif taco_type_string == "twitch_follow_count":
            return TacoTypes.TWITCH_FOLLOW
        elif taco_type_string == "twitch_stream_avatars":
            return TacoTypes.TWITCH_STREAM_AVATARS
        elif taco_type_string == "twitch_custom":
            return TacoTypes.TWITCH_CUSTOM
        else:
            return TacoTypes.CUSTOM

    @staticmethod
    def get_db_type_from_taco_type(taco_type):
        return taco_type.name.upper()

    @staticmethod
    def get_string_from_taco_type(taco_type):
        if taco_type == TacoTypes.JOIN_SERVER:
            return "join_count"
        elif taco_type == TacoTypes.BOOST:
            return "boost_count"
        elif taco_type == TacoTypes.REACT_REWARD:
            return "reaction_reward_count"
        elif taco_type == TacoTypes.SUGGEST:
            return "suggest_count"
        elif taco_type == TacoTypes.USER_INVITE:
            return "invite_count"
        elif taco_type == TacoTypes.REACTION:
            return "reaction_count"
        elif taco_type == TacoTypes.REPLY:
            return "reply_count"
        elif taco_type == TacoTypes.TQOTD:
            return "tqotd_count"
        elif taco_type == TacoTypes.BIRTHDAY:
            return "birthday_count"
        elif taco_type == TacoTypes.TWITCH_LINK:
            return "twitch_count"
        elif taco_type == TacoTypes.STREAM:
            return "stream_count"
        elif taco_type == TacoTypes.PHOTO_POST:
            return "photo_post_count"
        elif taco_type == TacoTypes.WDYCTW:
            return "wdyctw_count"
        elif taco_type == TacoTypes.TECH_THURSDAY:
            return "tech_thursday_count"
        elif taco_type == TacoTypes.TACO_TUESDAY:
            return "taco_tuesday_count"
        elif taco_type == TacoTypes.MENTAL_MONDAY:
            return "mental_monday_count"
        elif taco_type == TacoTypes.FIRST_MESSAGE:
            return "first_message_count"
        elif taco_type == TacoTypes.EVENT_CREATE:
            return "event_create_count"
        elif taco_type == TacoTypes.EVENT_JOIN:
            return "event_join_count"
        elif taco_type == TacoTypes.EVENT_LEAVE:
            return "event_leave_count"
        elif taco_type == TacoTypes.EVENT_CANCEL:
            return "event_cancel_count"
        elif taco_type == TacoTypes.EVENT_COMPLETE:
            return "event_complete_count"
        elif taco_type == TacoTypes.PURGE:
            return "purge_custom"
        elif taco_type == TacoTypes.LEAVE_SERVER:
            return "leave_server_custom"
        elif taco_type == TacoTypes.GAME_REDEEM:
            return "game_key_cost"
        elif taco_type == TacoTypes.GAME_DONATE_REDEEM:
            return "game_donate_count"
        elif taco_type == TacoTypes.TRIVIA_CORRECT:
            return "trivia_correct_count"
        elif taco_type == TacoTypes.TRIVIA_INCORRECT:
            return "trivia_incorrect_count"
        elif taco_type == TacoTypes.FOLLOW_CHANNEL:  # this can't be triggered by events
            return "follow_channel_count"
        elif taco_type == TacoTypes.CREATE_VOICE_CHANNEL:
            return "create_voice_channel_count"
        elif taco_type == TacoTypes.POST_INTRODUCTION:
            return "post_introduction_count"
        elif taco_type == TacoTypes.APPROVE_INTRODUCTION:
            return "approve_introduction_count"
        elif taco_type == TacoTypes.TWITCH_BOT_INVITE:
            return "twitch_bot_invite_count"
        elif taco_type == TacoTypes.TWITCH_RAID:
            return "twitch_raid_count"
        elif taco_type == TacoTypes.TWITCH_SUB:
            return "twitch_sub_count"
        elif taco_type == TacoTypes.TWITCH_BITS:
            return "twitch_bits_count"
        elif taco_type == TacoTypes.TWITCH_FIRST_MESSAGE:
            return "twitch_first_message_count"
        elif taco_type == TacoTypes.TWITCH_PROMOTE:
            return "twitch_promote_count"
        elif taco_type == TacoTypes.TWITCH_GIVE_TACOS:
            return "twitch_give_tacos"
            # this property is not saved in settings, as it should be the amount they give
        elif taco_type == TacoTypes.TWITCH_RECEIVE_TACOS:
            return "twitch_receive_tacos"
            # this property is not saved in settings, as it should be the amount they give
        elif taco_type == TacoTypes.TWITCH_FOLLOW:
            return "twitch_follow_count"
        elif taco_type == TacoTypes.TWITCH_STREAM_AVATARS:
            return "twitch_stream_avatars"
        elif taco_type == TacoTypes.TWITCH_CUSTOM:
            return "twitch_custom"
        else:
            return "custom"
