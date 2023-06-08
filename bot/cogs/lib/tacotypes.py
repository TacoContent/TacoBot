### NOTE: UPDATE THIS FILE WHEN CHANGING TACO TYPES ###
### UPDATE TacoBotTwitch/cogs/lib/tacotypes.py WHEN CHANGING TACO TYPES ###

from enum import Enum
class TacoTypes(Enum):
    JOIN = 1
    BOOST = 2
    REACT_REWARD = 3
    SUGGEST = 4
    INVITE = 5
    REACTION = 6
    REPLY = 7
    TQOTD = 8
    BIRTHDAY = 9
    TWITCH = 10
    STREAM = 11
    FOOD_PHOTO = 12
    WDYCTW = 13
    TECH_THURSDAY = 14
    TACO_TUESDAY = 15
    MENTAL_MONDAY = 16
    FIRST_MESSAGE = 17

    TWITCH_CUSTOM = 9998
    CUSTOM = 9999

    @staticmethod
    def get_from_string(taco_type_string):
        if taco_type_string == "join_count":
            return TacoTypes.JOIN
        elif taco_type_string == "boost_count":
            return TacoTypes.BOOST
        elif taco_type_string == "reaction_reward_count":
            return TacoTypes.REACT_REWARD
        elif taco_type_string == "suggest_count":
            return TacoTypes.SUGGEST
        elif taco_type_string == "invite_count":
            return TacoTypes.INVITE
        elif taco_type_string == "reaction_count":
            return TacoTypes.REACTION
        elif taco_type_string == "reply_count":
            return TacoTypes.REPLY
        elif taco_type_string == "tqotd_count":
            return TacoTypes.TQOTD
        elif taco_type_string == "birthday_count":
            return TacoTypes.BIRTHDAY
        elif taco_type_string == "twitch_count":
            return TacoTypes.TWITCH
        elif taco_type_string == "stream_count":
            return TacoTypes.STREAM
        elif taco_type_string == "food_photo_count":
            return TacoTypes.FOOD_PHOTO
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
        elif taco_type_string == "twitch_custom":
            return TacoTypes.TWITCH_CUSTOM
        else:
            return TacoTypes.CUSTOM

    @staticmethod
    def get_db_type_from_taco_type(taco_type):
        if taco_type == TacoTypes.JOIN:
            return "JOIN"
        elif taco_type == TacoTypes.BOOST:
            return "BOOST"
        elif taco_type == TacoTypes.REACT_REWARD:
            return "REACT_REWARD"
        elif taco_type == TacoTypes.SUGGEST:
            return "SUGGEST"
        elif taco_type == TacoTypes.INVITE:
            return "INVITE"
        elif taco_type == TacoTypes.REACTION:
            return "REACTION"
        elif taco_type == TacoTypes.REPLY:
            return "REPLY"
        elif taco_type == TacoTypes.TQOTD:
            return "TQOTD"
        elif taco_type == TacoTypes.BIRTHDAY:
            return "BIRTHDAY"
        elif taco_type == TacoTypes.TWITCH:
            return "TWITCH"
        elif taco_type == TacoTypes.STREAM:
            return "STREAM"
        elif taco_type == TacoTypes.FOOD_PHOTO:
            return "FOOD_PHOTO"
        elif taco_type == TacoTypes.WDYCTW:
            return "WDYCTW"
        elif taco_type == TacoTypes.TECH_THURSDAY:
            return "TECH_THURSDAY"
        elif taco_type == TacoTypes.TACO_TUESDAY:
            return "TACO_TUESDAY"
        elif taco_type == TacoTypes.MENTAL_MONDAY:
            return "MENTAL_MONDAY"
        elif taco_type == TacoTypes.FIRST_MESSAGE:
            return "FIRST_MESSAGE"
        elif taco_type == TacoTypes.TWITCH_CUSTOM:
            return "TWITCH_CUSTOM"
        else:
            return "CUSTOM"

    @staticmethod
    def get_string_from_taco_type(taco_type):
        if taco_type == TacoTypes.JOIN:
            return "join_count"
        elif taco_type == TacoTypes.BOOST:
            return "boost_count"
        elif taco_type == TacoTypes.REACT_REWARD:
            return "reaction_reward_count"
        elif taco_type == TacoTypes.SUGGEST:
            return "suggest_count"
        elif taco_type == TacoTypes.INVITE:
            return "invite_count"
        elif taco_type == TacoTypes.REACTION:
            return "reaction_count"
        elif taco_type == TacoTypes.REPLY:
            return "reply_count"
        elif taco_type == TacoTypes.TQOTD:
            return "tqotd_count"
        elif taco_type == TacoTypes.BIRTHDAY:
            return "birthday_count"
        elif taco_type == TacoTypes.TWITCH:
            return "twitch_count"
        elif taco_type == TacoTypes.STREAM:
            return "stream_count"
        elif taco_type == TacoTypes.FOOD_PHOTO:
            return "food_photo_count"
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
        elif taco_type == TacoTypes.TWITCH_CUSTOM:
            return "twitch_custom"
        else:
            return "custom"
