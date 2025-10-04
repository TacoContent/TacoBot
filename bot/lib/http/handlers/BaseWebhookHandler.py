"""Base webhook handler infrastructure.

This module defines :class:`BaseWebhookHandler`, a foundational class for
all inbound webhook-oriented HTTP handlers. It parallels
``BaseHttpHandler`` but focuses on functionality common to webhook
endpoints (notably token validation using the *webhook* settings
section).

Core Responsibilities
---------------------
* Provide initialized helper services: Discord helper, messaging,
    tracking database, settings manager, and structured logger.
* Standardize retrieval of guild-specific configuration sections.
* Offer a webhook token validation helper
    (:meth:`validate_webhook_token`) that checks for either
    ``X-TACOBOT-TOKEN`` or a backward-compatible ``X-AUTH-TOKEN`` header.
* Supply convenience accessors for commonly used settings namespaces
    (generic handler section and "tacos").

Token Validation Behavior
-------------------------
The ``validate_webhook_token`` method obtains the expected secret from
the ``webhook`` settings section (guild id 0). If the section or token
is missing it logs an error and returns ``False``. A request is accepted
only if the provided header value matches the stored token.

Security Notes
--------------
* The token comparison is constant-time only in the sense of Python's
    string equality semantics; if timing attacks become a concern, a
    hardened comparison (e.g., ``hmac.compare_digest``) could be used.
* A random fallback token seed is generated in the lookup expression to
    avoid accidental ``None`` comparisons; this guarantees mismatch while
    preventing exceptions.

Error Handling Philosophy
-------------------------
Most helper methods raise simple ``Exception`` derivatives for missing
configuration. Derived handlers are expected to translate those into
consistent JSON HTTP error responses (``{"error": "..."}``).
"""

import inspect
import os
import random
import string
import traceback

from bot.lib import discordhelper, logger, settings
from bot.lib.enums import loglevel
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from httpserver.http_util import HttpRequest


class BaseWebhookHandler:
    """Abstract base for all webhook handlers.

    Parameters
    ----------
    bot : Any
        Active bot instance supplying Discord client access and shared
        runtime context.
    """

    def __init__(self, bot):
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.SETTINGS_SECTION = "webhook"
        self.WEBHOOK_SETTINGS_SECTION = "webhook"
        self.settings = settings.Settings()

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)

    def get_cog_settings(self, guildId: int = 0) -> dict:
        """Return default webhook cog settings for a guild.

        Parameters
        ----------
        guildId : int, optional
            Discord guild ID; defaults to 0 (global scope).

        Returns
        -------
        dict
            Settings dictionary for the base webhook section.
        """
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        """Generic settings accessor with validation.

        Raises an exception if ``section`` is empty or missing for the
        provided guild ID.

        Parameters
        ----------
        guildId : int
            Guild identifier.
        section : str
            Settings section name.

        Returns
        -------
        dict
            Retrieved settings mapping.
        """
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        """Shortcut to retrieve the "tacos" settings section.

        Parameters
        ----------
        guildId : int, optional
            Discord guild ID (default 0 for global scope).

        Returns
        -------
        dict
            Taco economy related configuration.
        """
        return self.get_settings(guildId=guildId, section="tacos")

    def validate_webhook_token(self, request: HttpRequest) -> bool:
        """Validate the webhook authentication token in request headers.

        Header Precedence:
        1. ``X-TACOBOT-TOKEN``
        2. ``X-AUTH-TOKEN`` (fallback for legacy clients)

        Returns ``True`` only if a token is supplied and matches the
        stored secret in the ``webhook`` settings section (guild 0).
        Logs context-rich error messages for missing settings, missing
        token, or mismatch.

        Parameters
        ----------
        request : HttpRequest
            The inbound request object containing headers.

        Returns
        -------
        bool
            ``True`` if validation succeeds; otherwise ``False``.
        """
        _method = inspect.stack()[0][3]
        try:
            settings_obj = self.settings.get_settings(0, self.WEBHOOK_SETTINGS_SECTION)
            if not settings_obj:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "No settings found")
                return False

            token = request.headers.get("X-TACOBOT-TOKEN")
            if not token:
                # try to check X-AUTH-TOKEN
                token = request.headers.get("X-AUTH-TOKEN")
                if not token:
                    self.log.error(0, f"{self._module}.{self._class}.{_method}", "No token found in payload")
                    return False

            expected = settings_obj.get("token", ''.join(random.choices(string.ascii_uppercase + string.digits, k=24)))
            if token != expected:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "Invalid webhook token")
                return False

            return True
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            return False
