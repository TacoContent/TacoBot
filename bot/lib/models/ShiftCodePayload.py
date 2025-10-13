import time
import typing

from bot.lib.models.openapi import openapi_managed, openapi_model


@openapi_model("ShiftCodePayload", description="Payload for the SHiFT Code.")
@openapi_managed()
class ShiftCodePayload:
    def __init__(self, payload: dict):
        self.games: typing.List[ShiftCodeGame] = [ShiftCodeGame(game) for game in payload.get("games", [])]
        if not self.games:
            raise ValueError("Payload must contain at least one game.")

        self.code: str = payload.get("code", "")
        if not self.code:
            raise ValueError("Payload must contain a code.")
        self.platforms: typing.List[str] = payload.get("platforms", [])
        self.expiry: typing.Optional[int] = payload.get("expiry", None)
        self.reward: str = payload.get("reward", "")
        self.notes: str = payload.get("notes", "")
        self.source: str = payload.get("source", "")
        self.created_at: int = payload.get("created_at", 0)
        if not self.created_at:
            # set to current time using linux epoch time
            self.created_at = int(time.time())

    def to_dict(self) -> dict:
        return {
            "games": [game.to_dict() for game in self.games],
            "code": self.code,
            "platforms": self.platforms,
            "expiry": self.expiry,
            "reward": self.reward,
            "notes": self.notes,
            "source": self.source,
            "created_at": self.created_at,
        }


@openapi_model("ShiftCodeGame", description="Represents a supported game for SHiFT codes.")
@openapi_managed()
class ShiftCodeGame:
    def __init__(self, game: dict):
        self.id: str = game.get("id", "")
        self.name: str = game.get("name", "")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}
