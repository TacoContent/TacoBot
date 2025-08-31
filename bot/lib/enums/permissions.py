from enum import Enum


class TacoPermissions(Enum):
    UNKNOWN = 0
    CLAIM_GAME_DISABLED = 1

    def __str__(self) -> str:
        return self.name.lower()

    @staticmethod
    def from_str(event: str) -> "TacoPermissions":
        if event.lower() == "claim_game_disabled":
            return TacoPermissions.CLAIM_GAME_DISABLED
        else:
            return TacoPermissions.UNKNOWN
