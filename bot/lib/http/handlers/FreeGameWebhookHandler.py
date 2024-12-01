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
from httpserver.http_util import HttpHeaders, HttpRequest, HttpResponse
from httpserver.server import HttpResponseException, uri_mapping


class FreeGameWebhookHandler(BaseWebhookHandler):
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
        """Receive a free game payload from the webhook"""
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
            return HttpResponse(500)

    def _get_open_in_app_url(self, url: str) -> tuple[str, str]:
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
        if offer_type == FreeGameTypes.GAME:
            return "Game"
        elif offer_type == FreeGameTypes.DLC:
            return "Loot"
        else:
            return "Offer"

    def _get_offer_type(self, offer_type: str) -> FreeGameTypes:
        return FreeGameTypes.str_to_enum(offer_type)

    def _get_offer_platform(self, platform: str) -> FreeGamePlatforms:
        return FreeGamePlatforms.str_to_enum(platform)

    def _get_offer_platform_list(self, platforms: list) -> str:
        platform_list = []
        for platform in platforms:
            platform_list.append(str(self._get_offer_platform(platform)))
        # combine as a markdown list
        if len(platform_list) > 0:
            return "\n".join([f"- {platform}" for platform in platform_list])
        else:
            return "- Unknown"
