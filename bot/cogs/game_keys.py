import asyncio
import datetime
import inspect
import os
import traceback
import typing

import discord
from bot.lib import discordhelper, utils
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums import tacotypes
from bot.lib.messaging import Messaging
from bot.lib.mongodb.gamekeys import GameKeysDatabase
from bot.lib.mongodb.tacos import TacosDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.steam.steamapi import SteamApiClient
from bot.tacobot import TacoBot
from bot.ui.GameRewardView import GameRewardView
from discord.ext import commands


class GameKeysCog(TacobotCog):
    def __init__(self, bot: TacoBot):
        super().__init__(bot, "game_keys")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tacos_db = TacosDatabase()
        self.gamekeys_db = GameKeysDatabase()
        self.tracking_db = TrackingDatabase()
        self.steam_api = SteamApiClient()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized settings: {self.SETTINGS_SECTION}")

    @commands.Cog.listener()
    async def on_ready(self):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            guild_id = self.bot.guilds[0].id

            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"GameKeysCog is ready and loading cog settings: {self.SETTINGS_SECTION}",
            )
            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                return

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            offer = self.gamekeys_db.find_open_game_key_offer(guild_id=guild_id, channel_id=int(reward_channel_id))

            if offer:
                game_data = self.gamekeys_db.get_game_key_data(str(offer["game_key_id"]))
                if game_data:
                    default_cost = cog_settings.get("cost", 500)
                    cost = game_data.get("cost", default_cost)

                    if cost == 1:
                        tacos_word = self.settings.get_string(guild_id, "taco_singular")
                    else:
                        tacos_word = self.settings.get_string(guild_id, "taco_plural")

                    await self.bot.change_presence(
                        activity=discord.Game(name=f"{game_data['title']} ({cost} {tacos_word})")
                    )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_guild_available(self, guild):
        _method = inspect.stack()[0][3]
        try:
            # context = self.discord_helper.create_context(
            #     bot=self.bot, author=self.bot.user, channel=guild.system_channel, guild=guild
            # )
            # await self._create_offer(ctx=context)
            # await self._init_exiting_offer(ctx=context)
            pass
        except Exception as e:
            self.log.error(guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.group(name="game-keys", aliases=["gk", "gamekeys", "game-key", "gamekey", "games"])
    @commands.guild_only()
    async def game_keys(self, ctx):
        pass

    @game_keys.command(name="open", aliases=["o", "start", "s"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def open(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id
            await ctx.message.delete()
            await self._create_offer(ctx)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="game-keys",
                subcommand="open",
                args=[{"type": "command"}],
            )
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @game_keys.command(name="close")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def close(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id
            await ctx.message.delete()
            await self._close_offer(ctx)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="game-keys",
                subcommand="close",
                args=[{"type": "command"}],
            )
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def _create_offer(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            # if there is an existing offer, close it
            # then create a new offer
            await self._close_offer(ctx)

            # wait 3 seconds before creating a new offer
            await asyncio.sleep(3)

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"game_keys is disabled for guild {guild_id}"
                )
                return

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel = await self.discord_helper.get_or_fetch_channel(int(reward_channel_id))
            if not reward_channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No reward channel found for guild {guild_id}"
                )
                return

            offer = self.gamekeys_db.find_open_game_key_offer(guild_id, reward_channel.id)
            if offer:
                self.log.error(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"An existing open offer was found for guild {guild_id} in channel {reward_channel.name}. Ignoring request to create a new offer.",
                )
                return

            game_data = self.gamekeys_db.get_random_game_key_data(guild_id=guild_id)
            if not game_data:
                await reward_channel.send(
                    self.settings.get_string(guild_id, "game_key_no_keys_found_message"), delete_after=10
                )
                # log this as an error.
                self.log.error(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    self.settings.get_string(guild_id, "game_key_no_keys_found_message"),
                )
                return

            default_cost = cog_settings.get("cost", 500)
            cost = game_data.get("cost", default_cost)
            reset_cost = cog_settings.get("reset_cost", 100)

            if cost <= 0:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"Cost is 0 or less for guild {guild_id}"
                )
                return

            if cost == 1:
                tacos_word = self.settings.get_string(guild_id, "taco_singular")
            else:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            log_channel_id = cog_settings.get("log_channel_id", "0")
            log_channel = await self.discord_helper.get_or_fetch_channel(int(log_channel_id))
            if not log_channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No log channel found for guild {guild_id}"
                )
                return
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
                                    "final_formatted", price_overview.get('final_formatted', 'UNKNOWN')
                                )
                            else:
                                formatted_price = price_overview.get('final_formatted', 'UNKNOWN')
                            if formatted_price and formatted_price != 'UNKNOWN' and formatted_price != '':
                                formatted_price = f"~~{formatted_price}~~ "
                            description = data.get("short_description", "")
                            steam_info = f"\n\n{description}"
                            image_url = data.get("header_image", "")
                            # thumbnail = data.get("capsule_imagev5", "")
                        else:
                            self.log.warn(
                                guild_id,
                                f"{self._module}.{self._class}.{_method}",
                                f"Steam api call failed for App Id {app_id}",
                            )
                    else:
                        self.log.warn(
                            guild_id,
                            f"{self._module}.{self._class}.{_method}",
                            f"Steam App Details for App Id {app_id} not found",
                        )
                else:
                    self.log.warn(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Steam App Id not found in info_url: {info_url}",
                    )

            offered_by = await self.discord_helper.get_or_fetch_user(int(game_data["offered_by"]))
            expires = datetime.datetime.now() + datetime.timedelta(days=1)
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
                ctx=ctx,
                game_data=game_data,
                cost=cost,
                reset_cost=reset_cost,
                timeout=timeout,
                info_url=info_url,
            )

            notify_role_ids = cog_settings.get("notify_role_ids", [])
            notify_message = ""
            if notify_role_ids and len(notify_role_ids) > 0:
                # combine the role ids into a mention string that looks like <@&1234567890>
                notify_message = " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])

            offer_message = await self.messaging.send_embed(
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
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

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

    async def _reset_offer_callback(self, interaction: discord.Interaction):
        _method = inspect.stack()[0][3]
        if interaction.response.is_done():
            self.log.debug(
                interaction.guild.id,
                f"{self._module}.{self._class}.{_method}",
                "Reset offer cancelled because it was already responded to.",
            )
            return

        cog_settings = self.get_cog_settings(interaction.guild.id)
        guild_id = interaction.guild.id if interaction.guild else 0
        ctx = None

        if interaction.data["custom_id"] != "reset":
            self.log.warn(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Reset offer callback called with invalid custom_id: {interaction.data['custom_id']}",
            )
            return

        try:
            await interaction.response.defer()
        except Exception:
            # if the defer fails, we can't respond to the interaction
            return

        reset_cost = cog_settings.get("reset_cost", 100)
        reset_tacos_word = self.settings.get_string(guild_id, "taco_plural")
        if reset_cost == 1:
            reset_tacos_word = self.settings.get_string(guild_id, "taco_singular")

        try:
            # get the total taco count for the user
            taco_count = self.tacos_db.get_tacos_count(guild_id, interaction.user.id) or 0
            tacos_word = self.settings.get_string(guild_id, "taco_plural")
            if taco_count == 1:
                tacos_word = self.settings.get_string(guild_id, "taco_singular")

            if taco_count < reset_cost:
                await interaction.followup.send(
                    self.settings.get_string(
                        guild_id,
                        "game_key_reset_not_enough_tacos_message",
                        user=interaction.user.mention,
                        cost=reset_cost,
                        cost_tacos_word=reset_tacos_word,
                        taco_count=taco_count,
                        tacos_word=tacos_word,
                    ),
                    ephemeral=True,
                )
                return
            # create context from interaction
            ctx = self.discord_helper.create_context(
                self.bot,
                author=interaction.user,
                channel=interaction.channel,
                message=interaction.message,
                guild=interaction.guild,
                custom_id=interaction.data["custom_id"],
            )
            self.log.debug(
                guild_id, f"{self._module}.{self._class}.{_method}", f"Claiming offer {interaction.data['custom_id']}"
            )
            # charge the user the reset cost
            self.tacos_db.remove_tacos(guild_id, ctx.author.id, reset_cost)

            self.tacos_db.track_tacos_log(
                guildId=guild_id,
                fromUserId=ctx.author.id,
                toUserId=self.bot.user.id,
                count=reset_cost * -1,
                reason="New game key offer",
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(tacotypes.TacoTypes.GAME_KEY_RESET),
            )
            # create a new offer
            await self._create_offer(ctx)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    async def _claim_offer_callback(self, interaction: discord.Interaction):
        _method = inspect.stack()[0][3]
        if interaction.response.is_done():
            self.log.debug(
                interaction.guild.id,
                f"{self._module}.{self._class}.{_method}",
                "Claim offer cancelled because it was already responded to.",
            )
            return
        guild_id = interaction.guild.id if interaction.guild else 0
        ctx = None
        try:
            await interaction.response.defer()
        except Exception:
            # if the defer fails, we can't respond to the interaction
            return
        try:
            # create context from interaction
            ctx = self.discord_helper.create_context(
                self.bot,
                author=interaction.user,
                channel=interaction.channel,
                message=interaction.message,
                guild=interaction.guild,
                custom_id=interaction.data["custom_id"],
            )
            self.log.debug(
                guild_id, f"{self._module}.{self._class}.{_method}", f"Claiming offer {interaction.data['custom_id']}"
            )
            claim_result = await self._claim_offer(ctx, interaction.data["custom_id"])
            # if false, the claim failed and we need to re-enable the view
            if not claim_result:
                # create a claim view
                game_data = self.gamekeys_db.get_game_key_data(interaction.data["custom_id"])
                if game_data:
                    cog_settings = self.get_cog_settings(guild_id)
                    default_cost = cog_settings.get("cost", 500)
                    cost = game_data.get("cost", default_cost)
                    reset_cost = cog_settings.get("reset_cost", 100)
                    timeout = 60 * 60 * 24
                    info_url = game_data.get("info_link", "UNAVAILABLE")
                    claim_view = self._create_claim_view(
                        ctx=ctx,
                        game_data=game_data,
                        cost=cost,
                        reset_cost=reset_cost,
                        timeout=timeout,
                        info_url=info_url,
                    )
                    await interaction.message.edit(view=claim_view)
                else:
                    self.log.warn(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Game data not found for game id '{interaction.data['custom_id']}'",
                    )
                    await self._create_offer(ctx)
            else:
                await self._create_offer(ctx)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    # , interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    async def _claim_timeout_callback(self, ctx):
        _method = inspect.stack()[0][3]
        try:
            # create context from interaction
            ctx = self.discord_helper.create_context(
                self.bot, author=ctx.author, channel=ctx.channel, message=ctx.message, guild=ctx.guild
            )
            self.log.debug(ctx.guild.id, f"{self._module}.{self._class}.{_method}", "Claim offer timed out")
            await self._create_offer(ctx)
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    # async def _wait_or_new_offer(self, ctx):
    #     try:
    #         await asyncio.wait_for(self.eternity(), timeout=1.0)
    #     except asyncio.TimeoutError:
    #         await self._create_offer(ctx)
    # async def eternity(self):
    #     # Sleep for 2 days
    #     await asyncio.sleep((60 * 60 * 24) * 2)

    async def _close_offer(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        # get the current offer and close it
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"game_keys is disabled for guild {guild_id}"
                )
                return

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel: typing.Union[discord.TextChannel, None] = await self.discord_helper.get_or_fetch_channel(
                int(reward_channel_id)
            )

            if not reward_channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No reward channel found for guild {guild_id}"
                )
                return

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
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Offer message not found for guild {guild_id}",
                    )
                    pass

                self.gamekeys_db.close_game_key_offer_by_message(guild_id, int(offer["message_id"]))
                await self.bot.change_presence(activity=None)
            else:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No open offer found for guild {guild_id} in channel {reward_channel.name}",
                )
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def _claim_offer(self, ctx, game_id: str) -> bool:
        _method = inspect.stack()[0][3]
        try:
            # claim the offer
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"game_keys is disabled for guild {guild_id}"
                )
                return False

            # limit: {
            #   time_period: 3600,
            #   count: 1
            # },
            # get limits from settings
            limits = cog_settings.get("limit", {"time_period": 3600, "count": 0})
            claim_limit = limits.get("count", 0)
            claim_time_period = limits.get("time_period", 3600)
            if claim_limit >= 1:
                # get the number of redemptions in time_period
                claim_count = self.gamekeys_db.get_claimed_key_count_in_timeframe(
                    guild_id, ctx.author.id, claim_time_period
                )
                if claim_count >= claim_limit:
                    await ctx.channel.send(
                        self.settings.get_string(
                            guild_id,
                            "game_key_claim_limit_reached_message",
                            user=ctx.author.mention,
                            claim_limit=claim_limit,
                            time_frame=utils.human_time_duration(claim_time_period),
                        ),
                        delete_after=10,
                    )
                    return False

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel: typing.Union[discord.TextChannel, None] = await self.discord_helper.get_or_fetch_channel(
                int(reward_channel_id)
            )
            log_channel_id = cog_settings.get("log_channel_id", "0")
            log_channel = await self.discord_helper.get_or_fetch_channel(int(log_channel_id))

            if not reward_channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No reward channel found for guild {guild_id}"
                )
                return False

            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Claiming offer {game_id} for guild {guild_id} in channel {reward_channel.name}",
            )

            offer = self.gamekeys_db.find_open_game_key_offer(guild_id, reward_channel.id)
            if not offer:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No offer found for channel {reward_channel.name} in guild {guild_id}",
                )
                return False

            # get the game data from the offer game_key_id
            game_data = self.gamekeys_db.get_game_key_data(str(offer["game_key_id"]))
            if not game_data:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No game_key found while looking up id '{offer['game_key_id']}'",
                )
                await ctx.channel.send(
                    self.settings.get_string(guild_id, "game_key_no_game_data_message"), delete_after=10
                )
                return False

            default_cost = cog_settings.get("cost", 500)
            cost = game_data.get("cost", default_cost)

            if cost == 1:
                tacos_word = self.settings.get_string(guild_id, "taco_singular")
            else:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            # does the user have enough tacos?
            taco_count: int = self.tacos_db.get_tacos_count(guild_id, ctx.author.id)
            if taco_count < cost:
                await ctx.channel.send(
                    self.settings.get_string(
                        guild_id,
                        "game_key_not_enough_tacos_message",
                        user=ctx.author.mention,
                        cost=cost,
                        tacos_word=tacos_word,
                        taco_count=taco_count,
                    ),
                    delete_after=10,
                )
                return False

            # check if the game key offer is expired
            # if offer["expires"] < datetime.datetime.utcnow():
            #     self.log.debug(
            #         guild_id,
            #         f"{self._module}.{self._class}.{_method}",
            #         f"Game key offer {game_id} expired for guild {guild_id} in channel {reward_channel.name}",
            #     )
            #     await ctx.channel.send(
            #         self.settings.get_string(guild_id, "game_key_offer_expired_message", user=ctx.author.mention), delete_after=10
            #     )
            #     return False

            if game_data["redeemed_by"] is not None:
                # already redeemed
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Game key {game_data['_id']} already redeemed by {game_data['redeemed_by']}",
                )
                await ctx.channel.send(
                    self.settings.get_string(guild_id, "game_key_already_redeemed_message", user=ctx.author.mention),
                    delete_after=10,
                )
                return False
            if str(game_id) != str(offer["game_key_id"]) or str(game_data["_id"]) != str(game_id):
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Requested game_id ('{str(game_id)}') with offer game_key_id ('{str(offer['game_key_id'])}') does not match offer game id '{str(game_data['_id'])}'",
                )
                return False

            # send them the game key
            if not game_data["key"]:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No game key found for game '{game_data['title']}' ({str(game_data['_id'])})",
                )
                await ctx.channel.send(
                    self.settings.get_string(guild_id, "game_key_unable_to_claim_message", user=ctx.author.mention),
                    delete_after=10,
                )
                # need to create a new ctx for this
                # bot=None, author=None, guild=None, channel=None, message=None, invoked_subcommand=None, **kwargs
                # new_ctx = self.discord_helper.create_context(self.bot, author=ctx.bot.user, guild=ctx.guild, channel=reward_channel, message=None, invoked_subcommand=None)
                # await self._create_offer(new_ctx)
                raise Exception(f"No game key found for game '{game_data['title']}' ({str(game_data['_id'])})")
            try:
                download_link = game_data["download_link"]
                if download_link:
                    download_link = f"\n\n{download_link}"
                else:
                    download_link = ""
                help_link = game_data["help_link"]
                if help_link:
                    help_link = f"\n\n{help_link}"
                else:
                    help_link = ""
                await ctx.author.send(
                    self.settings.get_string(
                        guild_id,
                        "game_key_claim_message",
                        game=game_data["title"],
                        game_key=game_data["key"],
                        platform=game_data["type"],
                        download_link=download_link,
                        help_link=help_link,
                    )
                )
            except discord.Forbidden:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Unable to send game key for game '{game_data['title']}' ({game_id})",
                )
                await ctx.channel.send(
                    self.settings.get_string(guild_id, "game_key_unable_to_send_message", user=ctx.author.mention),
                    delete_after=10,
                )
                return False
            # set the game as claimed
            self.gamekeys_db.claim_game_key_offer(game_id, ctx.author.id)
            # remove the tacos from the user
            self.tacos_db.remove_tacos(guild_id, ctx.author.id, cost)

            self.tacos_db.track_tacos_log(
                guildId=guild_id,
                fromUserId=ctx.author.id,
                toUserId=self.bot.user.id,
                count=cost * -1,
                reason="Claim game key",
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(tacotypes.TacoTypes.GAME_REDEEM),
            )
            # get the user that offered the game key
            offer_user = await self.discord_helper.get_or_fetch_user(int(game_data["user_owner"]))
            if offer_user:
                await self.discord_helper.taco_give_user(
                    guildId=guild_id,
                    fromUser=self.bot.user,
                    toUser=offer_user,
                    reason=f"Donated game key {game_data['title']} was claimed by {ctx.author.name}",
                    taco_amount=cost,
                    give_type=tacotypes.TacoTypes.GAME_DONATE_REDEEM,
                )

            # log that the offer was claimed
            if log_channel:
                await log_channel.send(
                    self.settings.get_string(
                        guild_id,
                        "game_key_claim_log_message",
                        user=f"{utils.get_user_display_name(ctx.author)}",
                        game=game_data["title"],
                        tacos=cost,
                        tacos_word=tacos_word,
                    )
                )
            return True
        except Exception as e:
            raise e

    # import current game key offer and add it to the client as a view
    async def _init_exiting_offer(self, ctx):
        _method = inspect.stack()[0][3]
        if not ctx.guild:
            return

        guild_id = ctx.guild.id
        self.log.info(
            guild_id,
            f"{self._module}.{self._class}.{_method}",
            f"Initializing existing game key offer for guild {guild_id}",
        )
        try:
            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"game_keys is disabled for guild {guild_id}"
                )
                return

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel: typing.Union[discord.TextChannel, None] = await self.discord_helper.get_or_fetch_channel(
                int(reward_channel_id)
            )

            if not reward_channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No reward channel found for guild {guild_id}"
                )
                return

            offer = self.gamekeys_db.find_open_game_key_offer(guild_id=guild_id, channel_id=reward_channel.id)
            if offer:
                # add the view
                self.log.info(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Adding game key offer view for existing offer in guild {guild_id}",
                )
                channel_id = int(offer["channel_id"])
                message_id = int(offer["message_id"])
                # get the message
                channel: discord.TextChannel = await self.discord_helper.get_or_fetch_channel(channel_id)
                if not channel:
                    self.log.warn(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"No channel found for game key offer in guild {guild_id}",
                    )
                    return
                message: discord.Message = await channel.fetch_message(message_id)
                if not message:
                    self.log.warn(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"No message found for game key offer in guild {guild_id}",
                    )
                    return

                # get the view from the message
                imported_view: discord.ui.View = discord.ui.View.from_message(message)
                if not imported_view:
                    self.log.warn(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"No view found for game key offer in guild {guild_id}",
                    )
                    return

                # add the view to the client
                self.bot.add_view(imported_view, message_id=message_id)

                # self._add_game_key_offer_view(ctx, offer)
            else:
                self.log.info(guild_id, f"{self._module}.{self._class}.{_method}", "No existing game key offer found")
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        _method = inspect.stack()[0][3]
        if not interaction.guild:
            return
        try:
            if interaction.response.is_done():
                self.log.debug(
                    interaction.guild.id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Interaction already responded to: {interaction}",
                )
                return

            self.log.debug(
                interaction.guild.id, f"{self._module}.{self._class}.{_method}", f"Interaction received: {interaction}"
            )

            # _claim_offer_callback
            if "custom_id" not in interaction.data:
                self.log.debug(
                    interaction.guild.id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No custom_id in interaction data: {interaction}",
                )
                return

            game_id = interaction.data["custom_id"]

            if game_id == "reset":
                await self._reset_offer_callback(interaction)
                return

            if not game_id:
                self.log.debug(
                    interaction.guild.id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Custom id is empty: {interaction}",
                )
                return

            # get the game data to check if the custom_id IS a game id
            game_data = self.gamekeys_db.get_game_key_data(str(game_id))
            if not game_data:
                self.log.debug(
                    interaction.guild.id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Custom id is not a game id: {interaction}",
                )
                return

            # trigger the callback
            await self._claim_offer_callback(interaction)

        except Exception as e:
            self.log.error(
                interaction.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc()
            )


async def setup(bot):
    await bot.add_cog(GameKeysCog(bot))
