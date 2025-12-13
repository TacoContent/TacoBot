

import asyncio
import datetime
import inspect
import typing

import discord
from bot.lib.exceptions import (
    ExistingOpenGameKeyOfferFoundException,
    IncompatibleChannelException,
    NegativeCostException,
    NoGameKeysFoundException,
)
from bot.lib.helpers import EntityHelper, MessageHelper
from bot.lib.mongodb.gamekeys import GameKeysDatabase
from bot.lib.settings import Settings
from bot.lib.steam.steamapi import SteamApiClient
from bot.tacobot import TacoBot
from bot.ui.GameRewardView import GameRewardView


class GameKeysHelper:
    def __init__(
        self,
        bot: TacoBot,
        settings: Settings,
        gamekeys_db: GameKeysDatabase,
        entity_helper: EntityHelper,
        message_helper: MessageHelper,
        steam_api: SteamApiClient
    ) -> None:
        self._module = self.__module__
        self._class = self.__class__.__name__
        self.bot = bot
        self.settings = settings
        self.gamekeys_db = gamekeys_db
        self.entity_helper = entity_helper
        self.message_helper = message_helper
        self.steam_api = steam_api
        self.SETTINGS_SECTION = "game_keys"

    async def close_offer(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        # get the current offer and close it
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                # self.log.debug(
                #     guild_id, f"{self._module}.{self._class}.{_method}", f"game_keys is disabled for guild {guild_id}"
                # )
                return

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel: typing.Optional[typing.Union[discord.TextChannel, discord.DMChannel, discord.Thread]] = (
                await self.entity_helper.get_or_fetch_channel(int(reward_channel_id))
            )

            if not reward_channel or not isinstance(reward_channel, discord.TextChannel):
                # self.log.warn(
                #     guild_id, f"{self._module}.{self._class}.{_method}", f"No reward channel found for guild {guild_id}"
                # )
                raise IncompatibleChannelException(
                    self.settings.get_string(
                        guild_id,
                        "game_key_no_compatible_channel_message",
                        guild_id=guild_id,
                    )
                )

            offer = self.gamekeys_db.find_open_game_key_offer(guild_id, reward_channel.id)
            if offer:
                try:
                    offer_message = await reward_channel.fetch_message(int(offer["message_id"]))
                    if offer_message:
                        try:
                            await offer_message.delete()
                        except Exception:
                            pass
                except discord.NotFound:
                    # self.log.debug(
                    #     guild_id,
                    #     f"{self._module}.{self._class}.{_method}",
                    #     f"Offer message not found for guild {guild_id}",
                    # )
                    pass

                self.gamekeys_db.close_game_key_offer_by_message(guild_id, int(offer["message_id"]))
                await self.bot.change_presence(activity=None)
            else:
                pass
                # self.log.debug(
                #     guild_id,
                #     f"{self._module}.{self._class}.{_method}",
                #     f"No open offer found for guild {guild_id} in channel {reward_channel.name}",
                # )
        except Exception as e:
            raise e
            # self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            # await self.messaging.notify_of_error(ctx)

    async def create_offer(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            # if there is an existing offer, close it
            # then create a new offer
            await self.close_offer(ctx)

            # wait 3 seconds before creating a new offer
            await asyncio.sleep(3)

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                # self.log.debug(
                #     guild_id, f"{self._module}.{self._class}.{_method}", f"game_keys is disabled for guild {guild_id}"
                # )
                return

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel = await self.entity_helper.get_or_fetch_channel(int(reward_channel_id))
            if not reward_channel or not isinstance(reward_channel, discord.TextChannel):
                raise IncompatibleChannelException(
                    self.settings.get_string(
                        guild_id,
                        "game_key_no_compatible_channel_message",
                        guild_id=guild_id,
                    )
                )

            offer = self.gamekeys_db.find_open_game_key_offer(guild_id, reward_channel.id)
            if offer:
                raise ExistingOpenGameKeyOfferFoundException(
                    self.settings.get_string(
                        guild_id,
                        "game_key_existing_open_offer_found_message",
                        guild_id=guild_id,
                        channel_name=reward_channel.name,
                    )
                )

            game_data = self.gamekeys_db.get_random_game_key_data(guild_id=guild_id)
            if not game_data:
                raise NoGameKeysFoundException(self.settings.get_string(guild_id, "game_key_no_keys_found_message"))

            default_cost = cog_settings.get("cost", 500)
            cost = game_data.get("cost", default_cost)
            reset_cost = cog_settings.get("reset_cost", 100)

            if cost <= 0:
                raise NegativeCostException(
                    self.settings.get_string(
                        guild_id,
                        "game_key_negative_cost_exception_message",
                        guild_id=guild_id,
                    )
                )

            if cost == 1:
                tacos_word = self.settings.get_string(guild_id, "taco_singular")
            else:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            log_channel_id = cog_settings.get("log_channel_id", "0")
            log_channel = await self.entity_helper.get_or_fetch_channel(int(log_channel_id))
            if not log_channel:
                raise IncompatibleChannelException(
                    self.settings.get_string(
                        guild_id,
                        "game_key_no_compatible_log_channel_message",
                        guild_id=guild_id,
                    )
                )

            platform = game_data.get("platform", "UNKNOWN")
            info_url = game_data.get("info_url", "UNAVAILABLE")
            steam_info = ""
            formatted_price = ""
            image_url = None
            # thumbnail = None

            if platform.lower() == "steam" and info_url != "UNAVAILABLE":
                # extract the app_id from the info_url
                app_id = self.steam_api.get_app_id_from_url(info_url)
                if app_id:
                    app_details = self.steam_api.get_app_details(app_id)
                    if app_details:
                        data = app_details[str(app_id)].get("data", {})
                        success = app_details[str(app_id)].get("success", False)
                        if success:
                            price_overview = data.get("price_overview", {})
                            if price_overview.get("initial_formatted", "") != "":
                                formatted_price = price_overview.get(
                                    "final_formatted", price_overview.get('final_formatted', ' ')
                                )
                            else:
                                formatted_price = price_overview.get('final_formatted', ' ')
                            if formatted_price and formatted_price != ' ' and formatted_price != '':
                                formatted_price = f"~~{formatted_price}~~ "
                            description = data.get("short_description", "")
                            steam_info = f"\n\n{description}"
                            image_url = data.get("header_image", "")
                            # thumbnail = data.get("capsule_imagev5", "")
                        # else:
                        #     self.log.warn(
                        #         guild_id,
                        #         f"{self._module}.{self._class}.{_method}",
                        #         f"Steam api call failed for App Id {app_id}",
                        #     )
                    # else:
                    #     self.log.warn(
                    #         guild_id,
                    #         f"{self._module}.{self._class}.{_method}",
                    #         f"Steam App Details for App Id {app_id} not found",
                    #     )
                # else:
                #     self.log.warn(
                #         guild_id,
                #         f"{self._module}.{self._class}.{_method}",
                #         f"Steam App Id not found in info_url: {info_url}",
                #     )

            offered_by = await self.entity_helper.get_or_fetch_user(int(game_data["offered_by"]))
            expires = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=1)
            fields = [
                {"name": self.settings.get_string(guild_id, "game"), "value": game_data.get("title", "UNKNOWN")},
                {"name": self.settings.get_string(guild_id, "platform"), "value": platform},
                {
                    "name": self.settings.get_string(guild_id, "cost"),
                    "value": f"{formatted_price}{cost} {tacos_word} 🌮",
                },
                {"name": self.settings.get_string(guild_id, "expires"), "value": f"<t:{int(expires.timestamp())}:R>"},
                {"name": self.settings.get_string(guild_id, "link"), "value": info_url},
            ]

            timeout = 60 * 60 * 24

            claim_view = self._create_claim_view(
                ctx=ctx, game_data=game_data, cost=cost, reset_cost=reset_cost, timeout=timeout, info_url=info_url
            )

            notify_role_ids = cog_settings.get("notify_role_ids", [])
            notify_message = ""
            if notify_role_ids and len(notify_role_ids) > 0:
                # combine the role ids into a mention string that looks like <@&1234567890>
                notify_message = " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])

            offer_message = await self.message_helper.send_embed(
                channel=reward_channel,
                title=self.settings.get_string(guild_id, "game_key_offer_title"),
                message=self.settings.get_string(
                    guild_id, "game_key_offer_message", cost=cost, tacos_word=tacos_word, steam_info=steam_info
                ),
                image=image_url,
                # adding the thumbnail causes the layout of the embed to be weird
                # thumbnail=thumbnail,
                fields=fields,
                content=f"{notify_message}",
                author=offered_by,
                view=claim_view,
            )

            await self.bot.change_presence(activity=discord.Game(name=f"{game_data['title']} ({cost} {tacos_word})"))

            # record offer
            self.gamekeys_db.open_game_key_offer(game_data["id"], guild_id, offer_message.id, ctx.channel.id)
        except Exception as e:
            raise e
            # self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            # await self.messaging.notify_of_error(ctx)

    def _create_claim_view(self, ctx, game_data, cost, reset_cost, timeout, info_url):
        return GameRewardView(
            ctx,
            game_id=str(game_data["id"]),
            claim_callback=self._claim_offer_callback,
            timeout_callback=self._claim_timeout_callback,
            reset_callback=self._reset_offer_callback,
            cost=cost,
            reset_cost=reset_cost,
            timeout=timeout,
            external_link=info_url,
        )

    async def _claim_offer_callback(self, interaction: discord.Interaction) -> None:
        pass  # Implementation of claim offer logic goes here

    async def _claim_timeout_callback(self, interaction: discord.Interaction) -> None:
        pass  # Implementation of claim timeout logic goes here

    async def _reset_offer_callback(self, interaction: discord.Interaction) -> None:
        pass  # Implementation of reset offer logic goes here

    def get_cog_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            # check for global settings
            cog_settings = self.settings.get_settings(0, section)
        # if we still dont have settings, raise an error
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId} or globally.")
        return cog_settings
