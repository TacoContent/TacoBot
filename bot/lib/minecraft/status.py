"""Minecraft server status helper.

This lightweight utility wraps the ``mcstatus`` library to retrieve the
current status of a Java Edition Minecraft server (MOTD, player counts,
latency, version, sample players, etc.). It provides a minimal
abstraction so higher‑level handlers or scheduled tasks can call a
single method and receive a typed ``JavaStatusResponse`` object.

Design Goals
------------
* Keep the surface area small (single responsibility: fetch status).
* Defer connection details & parsing to the well‑maintained ``mcstatus``
    library.
* Remain synchronous to match existing call sites; if asynchronous or
    batched polling becomes necessary, a future async variant or executor
    offloading layer can be introduced.

Typical Usage
-------------
>>> status = MinecraftStatus("play.example.net", 25565).get()
>>> print(status.players.online, "/", status.players.max)

Error Handling
--------------
This helper does not internally catch exceptions. Network errors,
timeouts, DNS failures, or protocol parsing issues raised by
``mcstatus`` will propagate to the caller, which should translate them
into application‑appropriate logging or HTTP errors.

Future Enhancements (not implemented)
------------------------------------
* Add optional timeout parameter.
* Introduce simple in‑memory caching with a short TTL to reduce query
    load when status is polled frequently.
* Provide an async interface using ``asyncio.to_thread`` or native async
    support if added upstream.
"""

import mcstatus
from mcstatus.status_response import JavaStatusResponse


class MinecraftStatus:
    """Encapsulates retrieval of a Minecraft Java server status.

    Parameters
    ----------
    host : str
        Hostname or IP address of the Minecraft server.
    port : int, optional
        Server port (default ``25565`` for standard Java servers).
    """

    def __init__(self, host: str, port: int = 25565):
        self.host = host
        self.port = port

    def get(self) -> JavaStatusResponse:
        """Query the server and return a ``JavaStatusResponse``.

        Returns
        -------
        JavaStatusResponse
            Rich status object including latency, version info, player
            counts, sample player list, and MOTD.

        Raises
        ------
        Any exception raised by ``mcstatus`` during lookup or status
        retrieval (e.g., socket timeout, DNS failure, protocol error).
        """
        server = mcstatus.JavaServer.lookup(f"{self.host}:{self.port}")
        status = server.status()
        return status
