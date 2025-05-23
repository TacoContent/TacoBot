from enum import Enum


class MinecraftPlayerEvents(Enum):
    UNKNOWN = 0
    LOGIN = 1
    LOGOUT = 2
    DEATH = 3

    def __str__(self) -> str:
        return self.name.lower()

    @staticmethod
    def from_str(event: str) -> "MinecraftPlayerEvents":
        if event.lower() == "login":
            return MinecraftPlayerEvents.LOGIN
        elif event.lower() == "logout":
            return MinecraftPlayerEvents.LOGOUT
        elif event.lower() == "death":
            return MinecraftPlayerEvents.DEATH
        else:
            return MinecraftPlayerEvents.UNKNOWN
