from enum import Enum


class FreeGamePlatforms(Enum):
    PC = 1
    DRM_FREE = 2
    ITCH_IO = 3
    STEAM = 4
    EPIC_GAMES_STORE = 5

    MOBILE = 10
    ANDROID = 11
    IOS = 12

    NINTENDO = 20
    NINTENDO_SWITCH = 21

    PLAYSTATION = 30
    PLAYSTATION_4 = 31
    PLAYSTATION_5 = 32

    XBOX = 40
    XBOX_ONE = 41
    XBOX_SERIES_X_S = 42

    OTHER = 999

    def __str__(self):
        if self == FreeGamePlatforms.PC:
            return "PC"
        elif self == FreeGamePlatforms.STEAM:
            return "Steam"
        elif self == FreeGamePlatforms.EPIC_GAMES_STORE:
            return "Epic Games Store"
        elif self == FreeGamePlatforms.ITCH_IO:
            return "itch.io"
        elif self == FreeGamePlatforms.DRM_FREE:
            return "DRM-Free"
        elif self == FreeGamePlatforms.MOBILE:
            return "Mobile"
        elif self == FreeGamePlatforms.ANDROID:
            return "Android"
        elif self == FreeGamePlatforms.IOS:
            return "iOS"
        elif self == FreeGamePlatforms.NINTENDO:
            return "Nintendo"
        elif self == FreeGamePlatforms.NINTENDO_SWITCH:
            return "Nintendo Switch"
        elif self == FreeGamePlatforms.PLAYSTATION:
            return "PlayStation"
        elif self == FreeGamePlatforms.PLAYSTATION_4:
            return "PlayStation 4"
        elif self == FreeGamePlatforms.PLAYSTATION_5:
            return "PlayStation 5"
        elif self == FreeGamePlatforms.XBOX:
            return "Xbox"
        elif self == FreeGamePlatforms.XBOX_ONE:
            return "Xbox One"
        elif self == FreeGamePlatforms.XBOX_SERIES_X_S:
            return "Xbox Series X|S"
        else:
            return "Other"

    @staticmethod
    def str_to_enum(value: str):
        if value.lower() == "pc":
            return FreeGamePlatforms.PC
        elif value.lower() == "steam":
            return FreeGamePlatforms.STEAM
        elif value.lower() == "epic games store":
            return FreeGamePlatforms.EPIC_GAMES_STORE
        elif value.lower() == "itch.io":
            return FreeGamePlatforms.ITCH_IO
        elif value.lower() == "drm-free":
            return FreeGamePlatforms.DRM_FREE
        elif value.lower() == "mobile":
            return FreeGamePlatforms.MOBILE
        elif value.lower() == "android":
            return FreeGamePlatforms.ANDROID
        elif value.lower() == "ios":
            return FreeGamePlatforms.IOS
        elif value.lower() == "nintendo":
            return FreeGamePlatforms.NINTENDO
        elif value.lower() == "nintendo switch":
            return FreeGamePlatforms.NINTENDO_SWITCH
        elif value.lower() == "playstation":
            return FreeGamePlatforms.PLAYSTATION
        elif value.lower() == "playstation 4":
            return FreeGamePlatforms.PLAYSTATION_4
        elif value.lower() == "playstation 5":
            return FreeGamePlatforms.PLAYSTATION_5
        elif value.lower() == "xbox":
            return FreeGamePlatforms.XBOX
        elif value.lower() == "xbox one":
            return FreeGamePlatforms.XBOX_ONE
        elif value.lower() == "xbox series x|s":
            return FreeGamePlatforms.XBOX_SERIES_X_S
        else:
            return FreeGamePlatforms.OTHER
