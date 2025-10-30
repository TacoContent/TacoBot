import typing

from bot.lib.models.openapi import openapi


@openapi.component(
    "MinecraftServerStatusMotd",
    description="Represents the message of the day (MOTD) information in a Minecraft server status response.",
)
@openapi.property("plain", description="The plain text version of the MOTD.")
@openapi.property("html", description="The HTML formatted version of the MOTD.")
@openapi.property("raw", description="The raw version of the MOTD with formatting codes.")
@openapi.property("ansi", description="The ANSI formatted version of the MOTD.")
@openapi.managed()
class MinecraftServerStatusMotd:
    """Container for the "message of the day" (MOTD) information in a Minecraft server status response."""

    def __init__(self, data: dict):
        self.plain: str = data.get("plain", "")
        self.html: str = data.get("html", "")
        self.raw: str = data.get("raw", "")
        self.ansi: str = data.get("ansi", "")


@openapi.component(
    "MinecraftServerStatusPlayers",
    description="Represents player count information in a Minecraft server status response.",
)
@openapi.property("online", description="Number of players currently online.")
@openapi.property("max", description="Maximum player capacity of the server.")
@openapi.managed()
class MinecraftServerStatusPlayers:
    """Container for player count information in a Minecraft server status response."""

    def __init__(self, data: dict):
        self.online: int = data.get("online", 0)
        self.max: int = data.get("max", 0)


@openapi.component(
    "MinecraftServerStatusVersion", description="Represents version information in a Minecraft server status response."
)
@openapi.property("name", description="The version name of the Minecraft server.")
@openapi.property("protocol", description="The protocol version number of the Minecraft server.")
@openapi.managed()
class MinecraftServerStatusVersion:
    """Container for version information in a Minecraft server status response."""

    def __init__(self, data: dict):
        self.name: str = data.get("name", "")
        self.protocol: int = data.get("protocol", 0)


@openapi.component("MinecraftServerStatus", description="Represents the status of a Minecraft server.")
@openapi.property("success", description="Whether the status query was successful.")
@openapi.property("host", description="The hostname or IP address of the Minecraft server.")
@openapi.property("status", description="The current status of the server (e.g., online, offline, unknown).")
@openapi.property("description", description="A brief description of the server.")
@openapi.property("motd", description="The message of the day (MOTD) information.")
@openapi.property("online", description="Whether the server is currently online.")
@openapi.property("latency", description="The latency to the server in milliseconds.")
@openapi.property("enforces_secure_chat", description="Whether the server enforces secure chat.")
@openapi.property("icon", description="The base64-encoded server icon image.")
@openapi.property("players", description="Player count information.")
@openapi.property("version", description="Version information of the server.")
@openapi.managed()
class MinecraftServerStatus:
    """Container for the overall Minecraft server status response."""

    def __init__(self, data: dict):
        self.success: bool = data.get("success", False)
        self.host: str = data.get("host", "")
        self.status: typing.Literal['online', 'offline', 'unknown'] = data.get("status", "unknown")
        self.description: str = data.get("description", "")
        self.motd: MinecraftServerStatusMotd = MinecraftServerStatusMotd(data.get("motd", {}))
        self.online: bool = data.get("online", False)
        self.latency: int = data.get("latency", 0)
        self.enforces_secure_chat: bool = data.get("enforces_secure_chat", False)
        self.icon: str = data.get("icon", "")
        self.players: MinecraftServerStatusPlayers = MinecraftServerStatusPlayers(data.get("players", {}))
        self.version: MinecraftServerStatusVersion = MinecraftServerStatusVersion(data.get("version", {}))
