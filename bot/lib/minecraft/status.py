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

# Async usage
>>> status = MinecraftStatus("play.example.net", 25565)
>>> async def check_status():
...     status_response = await status.aget()
...     print(status_response.players.online, "/", status_response.players.max)

Error Handling
--------------
This helper does not internally catch exceptions. Network errors,
timeouts, DNS failures, or protocol parsing issues raised by
``mcstatus`` will propagate to the caller, which should translate them
into application‑appropriate logging or HTTP errors.

Future Enhancements (not implemented)
------------------------------------
* Native async support if added upstream to ``mcstatus`` library.
"""

import asyncio
import time

import mcstatus
from mcstatus.responses import JavaStatusResponse


class MinecraftStatus:
    """Encapsulates retrieval of a Minecraft Java server status.

    This class implements simple in-memory caching with a 30-second TTL
    to reduce query load when status is polled frequently. Both synchronous
    (``get()``) and asynchronous (``aget()``) interfaces are provided.

    Parameters
    ----------
    host : str
        Hostname or IP address of the Minecraft server.
    port : int, optional
        Server port (default ``25565`` for standard Java servers).
    timeout : float, optional
        Timeout in seconds for the status query (default ``3``).
    cache_ttl : int, optional
        Time-to-live in seconds for the cached status response (default ``30``).
        Set to 0 to disable caching.
    """

    def __init__(self, host: str, port: int = 25565, timeout: float = 3, cache_ttl: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._cache = None
        self._cache_time = 0
        self._cache_ttl = cache_ttl  # TTL in seconds

    def get(self) -> JavaStatusResponse:
        """Query the server and return a ``JavaStatusResponse``.

        This method implements simple in-memory caching with a 30-second TTL
        to reduce query load when status is polled frequently. Cached responses
        are returned if available and not expired.

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
        current_time = time.time()

        # Check if we have a valid cached response
        if self._cache is not None and (current_time - self._cache_time) < self._cache_ttl:
            return self._cache

        # Cache is stale or missing, fetch new status
        server = mcstatus.JavaServer.lookup(f"{self.host}:{self.port}", timeout=self.timeout)
        status = server.status()

        # Cache the result
        self._cache = status
        self._cache_time = current_time

        return status

    async def aget(self) -> JavaStatusResponse:
        """Asynchronously query the server and return a ``JavaStatusResponse``.

        This method implements the same caching logic as ``get()`` but runs
        the synchronous ``mcstatus`` operations in a thread pool using
        ``asyncio.to_thread`` to avoid blocking the event loop.

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
        current_time = time.time()

        # Check if we have a valid cached response
        if self._cache is not None and (current_time - self._cache_time) < self._cache_ttl:
            return self._cache

        # Cache is stale or missing, fetch new status asynchronously
        server = await asyncio.to_thread(mcstatus.JavaServer.lookup, f"{self.host}:{self.port}", timeout=self.timeout)
        status = await asyncio.to_thread(server.status)

        # Cache the result
        self._cache = status
        self._cache_time = current_time

        return status
