"""Base HTTP handler infrastructure.

This module defines :class:`BaseHttpHandler`, the foundational class that
other HTTP and webhook handlers inherit from. It centralizes common
concerns required by higher-level handlers so each endpoint file can
focus on domain logic rather than setup plumbing.

Primary Responsibilities
------------------------
* Store references to the active bot instance and helper services
    (Discord helper, messaging, tracking DB, settings manager, logger).
* Provide convenience wrappers for retrieving guild-specific settings
    sections (generic, tacos) with consistent error signaling.
* Expose a shared authentication helper (:meth:`validate_auth_token`)
    used by webhooks or internal endpoints that rely on a pre-configured
    shared secret header.
* Normalize logging context (module + class + method) for structured
    log lines across derived handlers.

Settings & Sections
-------------------
``SETTINGS_SECTION``: Default section key ("http") used by
``get_cog_settings``.

``WEBHOOK_SETTINGS_SECTION``: Section key ("webhook") expected to contain
the authentication token (``token``) used to validate inbound webhook
requests.

Authentication Token Validation
-------------------------------
``validate_auth_token`` inspects the incoming request headers for either
``X-TACOBOT-TOKEN`` or a fallback header ``X-AUTH-TOKEN``. If a token is
present and matches the stored webhook settings token, authentication
passes. Otherwise it logs a context-rich error and returns ``False``.

If the settings object is missing or does not include a token, a random
24-character alphanumeric default is generated in the comparison
expression—effectively guaranteeing a mismatch while avoiding a crash.

Error Handling Philosophy
-------------------------
Helper methods raise generic exceptions for missing sections / settings.
Derived classes typically convert those into structured JSON HTTP
responses (``{"error": "..."}``). The base class itself only logs and
returns simple booleans where appropriate.
"""

import inspect
import json
import os
import random
import string
import traceback
import typing

from lib.models.ErrorStatusCodePayload import ErrorStatusCodePayload

from bot.lib import discordhelper, logger, settings
from bot.lib.enums import loglevel
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.tacobot import TacoBot
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException


class BaseHttpHandler:
    """Abstract base for all HTTP / webhook handlers.

    Provides shared service instances (settings, discord helper, logger,
    messaging, tracking DB) and utility methods for settings retrieval
    and token-based authentication.

    Parameters
    ----------
    bot : TacoBot
        The active bot instance, supplying event loop context, Discord
        client access, and shared caches.
    """

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.SETTINGS_SECTION = "http"
        self.WEBHOOK_SETTINGS_SECTION = "webhook"
        self.settings = settings.Settings()

        self.discord_helper = discord_helper or discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)

    def get_cog_settings(self, guildId: int = 0) -> dict:
        """Return the default HTTP cog settings for a guild.

        Parameters
        ----------
        guildId : int, optional
            Discord guild ID (defaults to 0 which often represents a
            global / default configuration scope in this project).

        Returns
        -------
        dict
            Settings dictionary for the ``http`` section.
        """
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        """Generic settings accessor with validation.

        Raises an exception if ``section`` is empty or missing from the
        settings store for the provided guild ID.

        Parameters
        ----------
        guildId : int
            Guild identifier used to scope settings.
        section : str
            Settings section key.

        Returns
        -------
        dict
            Settings for the specified guild & section.
        """
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        """Shortcut for retrieving the ``tacos`` configuration section.

        Parameters
        ----------
        guildId : int, optional
            Discord guild ID (defaults to 0 – global context).

        Returns
        -------
        dict
            Taco-related settings for the guild.
        """
        return self.get_settings(guildId=guildId, section="tacos")

    def validate_auth_token(self, request: HttpRequest) -> bool:
        """Validate request headers against stored webhook token.

        Checks ``X-TACOBOT-TOKEN`` first, then ``X-AUTH-TOKEN`` as a
        backward-compatible fallback. Logs explicit error reasons to aid
        operational debugging without revealing the expected token.

        Parameters
        ----------
        request : HttpRequest
            Inbound HTTP request wrapper containing headers.

        Returns
        -------
        bool
            ``True`` if the presented token matches the configured
            webhook token; ``False`` otherwise (including on exception).
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
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "Invalid authentication token")
                return False

            return True
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            return False

    def _create_error_response(
        self, status_code: int, error_message: str, headers: HttpHeaders, include_stacktrace: bool = False
    ) -> HttpResponse:
        """Create standardized error response.

        Args:
            status_code: HTTP status code
            error_message: Human-readable error message
            headers: HTTP headers to include
            include_stacktrace: Whether to include exception stacktrace

        Returns:
            HttpResponse with ErrorStatusCodePayload body
        """
        err_data = {"code": status_code, "error": error_message}
        if include_stacktrace:
            err_data["stacktrace"] = traceback.format_exc()

        err = ErrorStatusCodePayload(err_data)
        return HttpResponse(status_code, headers, json.dumps(err.to_dict()).encode("utf-8"))

    def _create_error_from_exception(
        self, exception: HttpResponseException, include_stacktrace: bool = False
    ) -> HttpResponse:
        """Create standardized error response from exception.

        Args:
            status_code: HTTP status code
            exception: Exception instance
            headers: HTTP headers to include
            include_stacktrace: Whether to include exception stacktrace
        Returns:
            HttpResponse with ErrorStatusCodePayload body
        """
        err_data = {
            "code": exception.status_code,
            "error": exception.body.decode("utf-8") if exception.body else "An error occurred",
        }
        if include_stacktrace:
            err_data["stacktrace"] = traceback.format_exc()

        err = ErrorStatusCodePayload(err_data)
        headers = HttpHeaders()
        [headers.add(k, v) for k, v in err_data.get("headers", {}).items()]
        return HttpResponse(err_data.get("code", 500), headers, json.dumps(err.to_dict()).encode("utf-8"))
