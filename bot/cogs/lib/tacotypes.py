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
        else:
            return TacoTypes.CUSTOM

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
        else:
            return "custom"
