import time
import typing

from bot.lib.models.openapi import openapi


@openapi.component("ShiftCodePayload", description="Payload for the SHiFT Code.")
@openapi.property("games", description="List of games associated with the SHiFT code.")
@openapi.property("code", description="The SHiFT code string.")
@openapi.property("platforms", description="List of platforms the SHiFT code is valid for.")
@openapi.property("expiry", description="The expiry timestamp of the SHiFT code, if any.")
@openapi.property("reward", description="Description of the reward associated with the SHiFT code.")
@openapi.property("notes", description="Additional notes about the SHiFT code.")
@openapi.property("source", description="Source from where the SHiFT code was obtained.")
@openapi.property("created_at", description="Timestamp when the SHiFT code was created.")
@openapi.managed()
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


@openapi.component("ShiftCodeGame", description="Represents a supported game for SHiFT codes.")
@openapi.property("id", description="The unique identifier for the game.")
@openapi.property("name", description="The name of the game.")
@openapi.managed()
class ShiftCodeGame:
    def __init__(self, game: dict):
        self.id: str = game.get("id", "")
        self.name: str = game.get("name", "")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}
