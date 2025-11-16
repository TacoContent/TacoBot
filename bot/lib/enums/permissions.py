from enum import Enum


class TacoPermissions(Enum):
    UNKNOWN = 0
    CLAIM_GAME_DISABLED = 1

    TACOS_NO_GIVE = 2
    TACOS_NO_RECEIVE = 3

    PULLTAB_NO_PURCHASE = 4
    PULLTAB_NO_REDEEM = 5

    def __str__(self) -> str:
        return self.name.lower()

    @staticmethod
    def from_str(event: str) -> "TacoPermissions":
        if event.lower() == "claim_game_disabled":
            return TacoPermissions.CLAIM_GAME_DISABLED
        elif event.lower() == "tacos_no_give":
            return TacoPermissions.TACOS_NO_GIVE
        elif event.lower() == "tacos_no_receive":
            return TacoPermissions.TACOS_NO_RECEIVE
        elif event.lower() == "pulltab_no_purchase":
            return TacoPermissions.PULLTAB_NO_PURCHASE
        elif event.lower() == "pulltab_no_redeem":
            return TacoPermissions.PULLTAB_NO_REDEEM
        else:
            return TacoPermissions.UNKNOWN

    @staticmethod
    def all_permissions() -> list["TacoPermissions"]:
        return list(TacoPermissions)
