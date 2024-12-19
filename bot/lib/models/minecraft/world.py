class MinecraftWorld:
    def __init__(self, guildId: int, name: str, worldId: str, active: bool):
        if not guildId:
            raise ValueError("guildId is required")
        if not name:
            raise ValueError("name is required")
        if not worldId:
            raise ValueError("worldId is required")
        if active is None:
            raise ValueError("active is required")
        self.guildId = guildId
        self.name = name
        self.worldId = worldId
        self.active = active

    def __str__(self) -> str:
        return f"{self.name} ({self.worldId})"

    def to_dict(self) -> dict:
        return self.__dict__
