"""Free Game Webhook Handler.

This handler receives inbound webhook POSTs describing limited-time free /
discounted game offers and distributes formatted Discord embed messages to
configured guild channels. It performs light enrichment:

* Expands/unwraps the incoming giveaway URL following redirects.
* Optionally shortens URLs via a configured shortener service.
* Attempts to construct a platform specific "open in launcher" deep link when
    supported (Steam / Epic / Microsoft Store) to improve user experience.
* Applies formatting for pricing (strikethrough original), end/ended relative
    timestamps, and platform listing.
* Avoids duplicate announcements per guild using a tracking database.

Error Model:
        * Authentication failures -> 401 JSON {"error": "Invalid webhook token"}
        * Missing body -> 400 JSON {"error": "No payload found in the request"}
        * Unhandled exceptions -> 500 JSON {"error": "Internal server error: <details>"}

Idempotency / Safety:
        The handler checks whether a given `game_id` is already tracked for a guild
        prior to posting, preventing duplicate notifications if the webhook retries.

Extensibility Notes:
        * Additional platform deep-link rules can be added in `_get_open_in_app_url`.
        * Future localization could parameterize static strings (e.g. "Ends", "FREE").
"""

import html
import inspect
import json
import os
import traceback

import requests
from bot.lib import utils
from bot.lib.enums.free_game_platforms import FreeGamePlatforms
from bot.lib.enums.free_game_types import FreeGameTypes
from bot.lib.http.handlers.BaseWebhookHandler import BaseWebhookHandler
from bot.lib.mongodb.free_game_keys import FreeGameKeysDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.UrlShortener import UrlShortener
from bot.ui.ExternalUrlButtonView import ExternalUrlButtonView
from httpserver.EndpointDecorators import uri_mapping
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException


class FreeGameWebhookHandler(BaseWebhookHandler):
    """Process incoming free game webhook payloads and broadcast announcements.

    Responsibilities:
        * Validate webhook authentication token.
        * Decode & log the raw payload for observability.
        * Enrich offer data (redirect resolution, URL shortening, deep links).
        * Format and send Discord embed messages to configured channels.
        * Record announcements in tracking DB to suppress duplicates.
    """

    def __init__(self, bot):
        super().__init__(bot)
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.SETTINGS_SECTION = "free_games"

        self.tracking_db = TrackingDatabase()
        self.freegame_db = FreeGameKeysDatabase()

        self.url_shortener = UrlShortener(
            api_url=os.getenv("SHORTENER_API_URL", None), access_token=os.getenv("SHORTENER_ACCESS_TOKEN", None)
        )

    @uri_mapping("/webhook/game", method="POST")
    async def game(self, request: HttpRequest) -> HttpResponse:
        """Handle inbound free game webhook event.

        Authentication:
            Expects a valid webhook token (``validate_webhook_token``). If
            invalid a 401 JSON response is returned.

        Request Body (JSON example – fields vary by source):
            {
                "game_id": "<unique id>",
                "title": "Game Title",
                "description": "<html / text>",
                "instructions": "<html / text>",
                "worth": "$19.99",
                "end_date": 1730419200,  # epoch seconds
                "open_giveaway_url": "https://...",
                "type": "GAME" | "DLC" | "OTHER",
                "platforms": ["steam", "epic", ...],
                ...
            }

        Behaviour Summary:
            * Validates auth & body presence.
            * Derives offer type/platform list and aesthetics.
            * Resolves and shortens URL; attempts launcher deep link.
            * Skips guilds where feature disabled or game already tracked.
            * Posts embed with buttons and role mentions.

        Returns:
            200 JSON echo of original payload on success.
            400 / 401 JSON error for client issues.
            500 JSON error for unexpected failures.
        """
        _method = inspect.stack()[0][3]

        try:
            headers = HttpHeaders()
            headers.add("Content-Type", "application/json")

            if not self.validate_webhook_token(request):
                raise HttpResponseException(401, headers, b'{ "error": "Invalid webhook token" }')
            if not request.body:
                raise HttpResponseException(400, None, b'{ "error": "No payload found in the request" }')

            payload = json.loads(request.body)
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"{json.dumps(payload, indent=4)}")

            game_id = payload.get("game_id", "")

            end_date = payload.get("end_date", None)
            price = payload.get("worth", "").upper()

            if not price or price == "N/A" or price == "FREE":
                price = ""

            if price and price != "":
                price = f"~~{price}~~ "

            if end_date:
                seconds_remaining = utils.get_seconds_until(end_date)
                if seconds_remaining <= 0:
                    end_date_msg = f"\nEnded: <t:{end_date}:R>"
                else:
                    end_date_msg = f"\nEnds: <t:{end_date}:R>"
            else:
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", "No end date found")
                end_date_msg = ""

            url = payload.get("open_giveaway_url", "")
            short_url = url
            open_in_app_url = ""
            open_in_app_name = ""
            # get final url
            if url and url != "":
                try:

                    r = requests.get(url, allow_redirects=True, headers={"Referer": url, "User-Agent": "Tacobot/1.0"})
                    url = r.url
                    short_url = self.url_shortener.shorten(url=url).get("url", url)
                    # get open_in_app url
                    # discord does not allow custom url schemes to be opened in the app

                    open_in_app_name, open_in_app_url = self._get_open_in_app_url(url)

                    # this will get the steam short link if the url is a steam store link
                    # url = self._get_open_url(url)

                    # disable the open_in_app_url for now
                    # open_in_app_name = ""
                    # open_in_app_url = ""

                    # cannot use bitly to shorten non-http(s) urls :(
                    open_in_app_url = self.url_shortener.shorten(url=open_in_app_url).get("url", open_in_app_url)
                    # url = self.url_shortener.shorten(long_url=url).get("link", url)
                except Exception as e:
                    self.log.warn(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
                    open_in_app_url = ""
                    open_in_app_name = ""

            # print(f"open_in_app_url: {open_in_app_url}")
            # print(f"open_in_app_name: {open_in_app_name}")
            # print(f"url: {url}")

            # return HttpResponse(200, headers, json.dumps(payload, indent=4).encode())

            offer_type = self._get_offer_type(payload.get("type", "OTHER"))
            offer_type_str = self._get_offer_type_str(offer_type)
            platform_list = self._get_offer_platform_list(payload.get("platforms", []))
            open_browser = f"[Claim {offer_type_str} ↗️]({short_url})" if short_url else ""
            open_app = f" / [Open in {open_in_app_name} ↗️]({open_in_app_url})\n\n" if open_in_app_url else ""
            desc = html.unescape(payload['description'])
            instructions = html.unescape(payload['instructions'])

            # take the payload, formulate a message, and send it to the specific channel based on each guild.
            # for testing purposes, we will just send the message to the first guild we find

            guilds = self.bot.guilds
            for guild in guilds:
                guild_id = guild.id
                fg_settings = self.get_settings(guild_id, self.SETTINGS_SECTION)

                if not fg_settings.get("enabled", False):
                    self.log.debug(
                        0, f"{self._module}.{self._class}.{_method}", f"Free Games is disabled for guild {guild_id}"
                    )
                    continue

                if self.freegame_db.is_game_tracked(guild_id, game_id):
                    self.log.debug(
                        0,
                        f"{self._module}.{self._class}.{_method}",
                        f"Game '{game_id}' for guild '{guild_id}' is already being tracked",
                    )
                    continue

                # get channel ids
                channel_ids = fg_settings.get("channel_ids", [])
                if not channel_ids or len(channel_ids) == 0:
                    self.log.debug(
                        0, f"{self._module}.{self._class}.{_method}", f"No channel ids found for guild {guild_id}"
                    )
                    continue

                channels = []
                for channel_id in channel_ids:
                    channel = await self.discord_helper.get_or_fetch_channel(int(channel_id))
                    if channel:
                        channels.append(channel)

                if len(channels) == 0:
                    self.log.debug(
                        0, f"{self._module}.{self._class}.{_method}", f"No channels found for guild {guild_id}"
                    )
                    continue

                notify_role_ids = fg_settings.get("notify_role_ids", [])
                notify_message = ""
                if notify_role_ids and len(notify_role_ids) > 0:
                    # combine the role ids into a mention string that looks like <@&1234567890>
                    notify_message = " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])

                fields = [{"name": "Platforms", "value": platform_list, "inline": True}]
                link_button = ExternalUrlButtonView(f"Claim {offer_type_str}", url)
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Sending message to channels: {channels}")
                for channel in channels:
                    message = await self.messaging.send_embed(
                        channel=channel,
                        title=f"{payload['title']} ↗️",
                        message=f"{price}**FREE**{end_date_msg}\n\n{desc}\n\n{instructions}\n\n{open_browser}{open_app}",
                        url=short_url,
                        # the thumbnail causes the layout of the embed to be weird
                        # thumbnail=payload['thumbnail'],
                        image=payload['image'],
                        delete_after=None,
                        fields=fields,
                        content=f"{notify_message}",
                        view=link_button,
                    )

                    self.tracking_db.track_free_game_key(
                        guildId=guild_id, channelId=channel.id, messageId=message.id, gameId=game_id
                    )

            return HttpResponse(200, headers, json.dumps(payload, indent=4).encode())

        except HttpResponseException as e:
            return HttpResponse(e.status_code, e.headers, e.body)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            if 'headers' not in locals():
                headers = HttpHeaders()
                headers.add("Content-Type", "application/json")
            err_msg = f'{{"error": "Internal server error: {str(e)}"}}'
            return HttpResponse(500, headers, bytearray(err_msg, "utf-8"))

    def _get_open_in_app_url(self, url: str) -> tuple[str, str]:
        """Return (launcher_name, deep_link_url) for supported platforms.

        Currently supports:
            * Microsoft Store (ms-windows-store://)
            * Steam (steam://openurl/...)
            * Epic Games Launcher (com.epicgames.launcher://)

        Returns empty tuple components when no mapping is available.
        """
        if not url or url == "":
            return "", ""

        # https://www.microsoft.com/en-us/p/hero-of-the-kingdom/9pgp1snbrc4j
        # https://apps.microsoft.com/detail/9p83lmp6gdpk?hl=en-us&gl=US
        # ms-windows-store://pdp?hl=en-us&gl=us&productid=9p83lmp6gdpk&mode=mini&pos=0%2C-1083%2C1920%2C1032&referrer=storeforweb

        if ".microsoft.com" in url:
            # get the product id from the url. it is the value after the last slash and before the query string
            # make sure to remove the query string and anchors before getting the slug
            # if there is a / before the query string marker, remove it
            slug = url.replace("/?", "?").split("/")[-1].split("?")[0]
            return (
                "Microsoft Store",
                f"ms-windows-store://pdp?productid={slug}&mode=mini&hl=en-us&gl=US&referrer=storeforweb",
            )

        if "store.steampowered.com" in url:
            return "Steam", f"steam://openurl/{url}"

        if "epicgames.com" in url:
            # trim off the query string or anchors, and remove trailing slashes before getting the slug
            slug = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
            return "Epic Games Launcher", f"com.epicgames.launcher://store/p/{slug}"

        return "", ""

    def _get_open_url(self, url: str) -> str:
        """(Placeholder) Potential transformation for public sharing URL.

        Currently returns the original URL; retained for future expansion
        (e.g., converting Steam store URLs to short-form share links).
        """
        if not url or url == "":
            return ""

        # if "store.steampowered.com" in url:
        #     # remove the query string, anchors, and trailing slashes
        #     url = url.split("?")[0].split("#")[0].rstrip("/")
        #     # get app id from the url
        #     app_id = url.split("/")[-2]
        #     return f"https://s.team/a/{app_id}"

        return url

    def _get_offer_type_str(self, offer_type: FreeGameTypes) -> str:
        """Map enum offer type to human-readable string for embed labels."""
        if offer_type == FreeGameTypes.GAME:
            return "Game"
        elif offer_type == FreeGameTypes.DLC:
            return "Loot"
        else:
            return "Offer"

    def _get_offer_type(self, offer_type: str) -> FreeGameTypes:
        """Convert string (case-insensitive) to ``FreeGameTypes`` enum."""
        return FreeGameTypes.str_to_enum(offer_type)

    def _get_offer_platform(self, platform: str) -> FreeGamePlatforms:
        """Convert platform string to ``FreeGamePlatforms`` enum."""
        return FreeGamePlatforms.str_to_enum(platform)

    def _get_offer_platform_list(self, platforms: list) -> str:
        """Format platform list as a Markdown bullet string for embedding.

        Returns a hyphenated list or a single ``- Unknown`` entry when empty.
        """
        platform_list = []
        for platform in platforms:
            platform_list.append(str(self._get_offer_platform(platform)))
        # combine as a markdown list
        if len(platform_list) > 0:
            return "\n".join([f"- {platform}" for platform in platform_list])
        else:
            return "- Unknown"
