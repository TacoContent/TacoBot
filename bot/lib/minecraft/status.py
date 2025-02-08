import mcstatus
from mcstatus.status_response import JavaStatusResponse


class MinecraftStatus:
    def __init__(self, host: str, port: int = 25565):
        self.host = host
        self.port = port

    def get(self) -> JavaStatusResponse:
        server = mcstatus.JavaServer.lookup(f"{self.host}:{self.port}")
        status = server.status()
        return status
