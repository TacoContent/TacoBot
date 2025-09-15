import time


class ShiftCodePayload:
    def __init__(self, payload: dict):
        self.games = [ShiftCodeGame(game) for game in payload.get("games", [])]
        if not self.games:
            raise ValueError("Payload must contain at least one game.")

        self.code = payload.get("code")
        if not self.code:
            raise ValueError("Payload must contain a code.")
        self.platforms = payload.get("platforms", [])
        self.expiry = payload.get("expiry", None)
        self.reward = payload.get("reward", "")
        self.notes = payload.get("notes", "")
        self.source = payload.get("source", "")
        self.created_at = payload.get("created_at")
        if not self.created_at:
            # set to current time using linux epoch time
            self.created_at = time.time()

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


class ShiftCodeGame:
    def __init__(self, game: dict):
        self.id = game.get("id")
        self.name = game.get("name")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}
