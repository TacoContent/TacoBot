import os
import typing
from http import HTTPMethod

from httpserver.EndpointDecorators import uri_variable_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from lib import discordhelper
from lib.enums.minecraft_player_events import MinecraftPlayerEventLiteral
from lib.http.handlers.ApiHttpHandler import ApiHttpHandler
from lib.models import MinecraftPlayerEventPayload
from lib.models.openapi import openapi
from lib.mongodb.minecraft import MinecraftDatabase
from lib.mongodb.tracking import TrackingDatabase
from lib.settings import Settings
from tacobot import TacoBot


class NodeRedApiHandler(ApiHttpHandler):
    """
    This is a placeholder for Node-RED API handler.
    """

    def __init__(self, bot: TacoBot, discord_helper: typing.Optional[discordhelper.DiscordHelper] = None):
        super().__init__(bot, discord_helper)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "http"
        self.NODERED_URL = "https://nodered.bit13.local"

        self.settings = Settings()

        self.minecraft_db = MinecraftDatabase()
        self.tracking_db = TrackingDatabase()

    @uri_variable_mapping("/tacobot/minecraft/player/event/{event}")
    @uri_variable_mapping("/taco/minecraft/player/event/{event}")
    @uri_variable_mapping("/api/v1/minecraft/player/event/{event}")
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Redirect Minecraft player event to Node-RED")
    @openapi.pathParameter(
        name="event",
        schema=MinecraftPlayerEventLiteral,
        description="Type of Minecraft player event to redirect.",
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.description("This endpoint redirects Minecraft player events to a Node-RED flow.")
    @openapi.response(
        200,
        description="Successful trigger of the event.",
        contentType="application/json",
        schema=MinecraftPlayerEventPayload,
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.response(
        302,
        description="If called directly to TacoBot, it will redirect to Node-RED.",
        methods=[HTTPMethod.GET, HTTPMethod.POST],
    )
    @openapi.tags("minecraft", "nodered")
    @openapi.managed()
    def minecraft_player_event(self, request: HttpRequest, uri_variables: typing.Dict[str, typing.Any]) -> HttpResponse:
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")
        event: str = uri_variables.get("event", "")

        if not event:
            return self._create_error_response(400, "Event type is required", headers=headers)

        headers.add("Location", f"{self.NODERED_URL}/minecraft/player/event/{event}")
        return self._create_error_response(302, f"Redirecting to Node-RED for event: {event}", headers=headers)

    @uri_variable_mapping("/tacobot/guild/{guild}/invite/{channel}", method=HTTPMethod.POST)
    @uri_variable_mapping("/taco/guild/{guild}/invite/{channel}", method=HTTPMethod.POST)
    @uri_variable_mapping("/api/v1/guild/{guild}/invite/{channel}", method=HTTPMethod.POST)
    @openapi.security("X-AUTH-TOKEN", "X-TACOBOT-TOKEN")
    @openapi.summary("Redirect Twitch guild invite to Node-RED")
    @openapi.pathParameter(name="guild", schema=str, description="ID of the guild to invite.", methods=HTTPMethod.POST)
    @openapi.pathParameter(
        name="channel", schema=str, description="ID of the channel to invite.", methods=HTTPMethod.POST
    )
    @openapi.description("This endpoint redirects to a Node-RED flow.")
    @openapi.response(
        200,
        description="Successful trigger of the event.",
        contentType="application/json",
        schema=typing.Dict[str, typing.Any],
        methods=HTTPMethod.POST,
    )
    @openapi.response(
        302, description="If called directly to TacoBot, it will redirect to Node-RED.", methods=HTTPMethod.POST
    )
    @openapi.tags("minecraft", "nodered")
    @openapi.managed()
    def twitch_guild_invite(self, request: HttpRequest, uri_variables: typing.Dict[str, typing.Any]) -> HttpResponse:
        headers = HttpHeaders()
        headers.add("Content-Type", "application/json")

        guild: str = uri_variables.get("guild", "")
        channel: str = uri_variables.get("channel", "")

        if not guild:
            return self._create_error_response(400, "Guild ID is required", headers=headers)

        if not channel:
            return self._create_error_response(400, "Channel ID is required", headers=headers)

        headers.add("Location", f"{self.NODERED_URL}/tacobot/guild/{guild}/invite/{channel}")
        return self._create_error_response(302, "Redirecting to Node-RED for Twitch guild invite", headers=headers)
