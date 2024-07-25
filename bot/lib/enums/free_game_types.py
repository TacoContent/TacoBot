from enum import Enum


class FreeGameTypes(Enum):
    GAME = 1
    DLC = 2
    EARLY_ACCESS = 3
    DEMO = 4
    OTHER = 999

    @staticmethod
    def str_to_enum(value: str):
        if value.lower() == "game":
            return FreeGameTypes.GAME
        elif value.lower() == "dlc":
            return FreeGameTypes.DLC
        elif value.lower() == "early access":
            return FreeGameTypes.EARLY_ACCESS
        elif value.lower() == "demo":
            return FreeGameTypes.DEMO
        else:
            return FreeGameTypes.OTHER
