"""Generic internal API helper / facade for outbound service calls.

This module currently provides a thin HTTP wrapper used to call a
Node-RED instance (``NODERED_URL``) from inside the bot's HTTP layer.
Its responsibilities are intentionally narrow:

* Centralize base URL construction for Node-RED flows.
* Provide a single private helper (``_nodered_request``) that abstracts
    method dispatch and basic non-200 error surfacing.
* Offer convenient access to project settings / Mongo database helpers
    (Minecraft + tracking) should future public endpoints be added here.

Scope & Design Notes
--------------------
* The handler inherits from :class:`BaseHttpHandler` for shared logging,
    configuration, and request/response utilities used across the codebase.
* Only a private helper is defined at present; no external HTTP routes
    are registered in this file. When adding routes later, keep response
    JSON error shape consistent with other handlers (``{"error": "..."}``).
* TLS Verification is explicitly disabled (``verify=False``) in outbound
    ``requests`` calls. This is acceptable only for controlled internal
    environments / development. For production or exposed networks you
    should enable certificate verification or inject a trusted CA bundle.
* Exceptions are re-raised with simplified messages; upstream callers
    are expected to convert them into structured HTTP responses.

Potential Future Enhancements
-----------------------------
* Add timeout handling and retries with backoff.
* Support streaming responses / large payloads.
* Provide structured exceptions instead of generic ``Exception``.
* Allow per-request override of ``verify`` and timeouts.
"""

import os
import typing

import requests
from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from lib import discordhelper
from tacobot import TacoBot


class ApiHttpHandler(BaseHttpHandler):
    """Internal API helper handler.

    While other handlers expose HTTP endpoints via decorators, this
    class currently serves as an integration utility for calling the
    configured Node-RED instance. It can be expanded later with
    outward-facing endpoints that proxy or orchestrate multiple
    downstream services.
    """

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "http"
        self.NODERED_URL = "https://nodered.bit13.local"

        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)
        self.settings = Settings()

        self.minecraft_db = MinecraftDatabase()
        self.tracking_db = TrackingDatabase()

    def _nodered_request(
        self, endpoint: str, method: str, headers: typing.Optional[dict] = None, data: typing.Optional[dict] = None
    ) -> requests.Response:
        """Perform an HTTP request against the configured Node-RED base URL.

        Parameters
        ----------
        endpoint : str
            Relative path (leading slash expected) appended to ``NODERED_URL``.
        method : str
            HTTP verb. Supported: ``GET``, ``POST``, ``PUT``, ``DELETE``.
        headers : dict, optional
            Optional HTTP headers to include.
        data : dict, optional
            JSON-serializable body for ``POST`` / ``PUT`` requests.

        Returns
        -------
        requests.Response
            The underlying ``requests`` library response object when the
            status code is 200.

        Raises
        ------
        Exception
            If an unsupported method is provided, the response status
            code is not 200, or a request/transport error occurs. The
            raised message includes a simplified human-readable string.

        Security Considerations
        -----------------------
        TLS certificate verification is disabled (``verify=False``),
        which should only be used for trusted internal services. To
        harden this, remove ``verify=False`` or supply a CA bundle.
        """
        try:
            url = f"{self.NODERED_URL}{endpoint}"
            if method == "GET":
                response = requests.get(url, headers=headers, verify=False)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, verify=False)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, verify=False)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, verify=False)
            else:
                raise Exception(f"Unsupported method: {method}")

            if response.status_code != 200:
                raise Exception(f"Error {response.status_code}: {response.text}")

            return response
        except Exception as e:
            raise Exception(f"Error calling Node-RED: {str(e)}")
