import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import inspect
import collections
import datetime

from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import tacotypes
from .lib.GameRewardView import GameRewardView

class GameKeys(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "game_keys"
        self.db = mongo.MongoDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", "Initialized")

    @commands.group(name="game-keys")
    @commands.guild_only()
    async def game_keys(self, ctx):
        pass

    @game_keys.command(name="open")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def open(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        try:
            await ctx.message.delete()
            await self._create_offer(ctx)
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @game_keys.command(name="close")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def close(self, ctx):
        _method = inspect.stack()[0][3]
        try:
            await ctx.message.delete()
            await self._close_offer(ctx)
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    async def _create_offer(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            # if there is an existing offer, close it
            # then create a new offer
            await self._close_offer(ctx)

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, f"{self._module}.{_method}", f"game_keys is disabled for guild {guild_id}")
                return

            # Should we pull this from `tacos` settings?
            cost = cog_settings.get("cost", 500)
            if cost <= 0:
                self.log.warn(guild_id, f"{self._module}.{_method}", f"Cost is 0 or less for guild {guild_id}")
                return

            if cost == 1:
                tacos_word = self.settings.get_string(guild_id, "taco_singular")
            else:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel = await self.discord_helper.get_or_fetch_channel(int(reward_channel_id))
            log_channel_id = cog_settings.get("log_channel_id", "0")
            log_channel = await self.discord_helper.get_or_fetch_channel(int(log_channel_id))
            if not reward_channel:
                self.log.warn(guild_id, f"{self._module}.{_method}", f"No reward channel found for guild {guild_id}")
                return
            if not log_channel:
                self.log.warn(guild_id, f"{self._module}.{_method}", f"No log channel found for guild {guild_id}")
                return

            game_data = self.db.get_random_game_key_data(guild_id=guild_id)
            if not game_data:
                await ctx.send(self.settings.get_string(guild_id, "game_key_no_keys_found_message"), delete_after=10)
                return

            offered_by = await self.bot.fetch_user(int(game_data["offered_by"]))
            expires = datetime.datetime.now() + datetime.timedelta(days=1)
            fields = [

                {"name": self.settings.get_string(guild_id, "game"), "value": game_data.get("title", "UNKNOWN")},
                {"name": self.settings.get_string(guild_id, "platform"), "value": game_data.get("platform", "UNKNOWN")},
                {"name": self.settings.get_string(guild_id, "cost"), "value": f"{cost} {tacos_word}🌮"},
                {
                    "name": self.settings.get_string(guild_id, "link"),
                    "value": game_data.get("info_url", "[Unavailable]"),
                },
                {
                    "name": self.settings.get_string(guild_id, "expires"),
                    "value": f"{expires.strftime('%Y-%m-%d %H:%M:%S')} UTC",
                },
            ]
            timeout = 60 * 60 * 24

            claim_view = GameRewardView(
                ctx,
                game_id=str(game_data["id"]),
                claim_callback=self._claim_offer_callback,
                timeout_callback=self._claim_timeout_callback,
                cost=cost,
                timeout=timeout
            )

            offer_message = await self.discord_helper.sendEmbed(
                reward_channel,
                self.settings.get_string(guild_id, "game_key_offer_title"),
                self.settings.get_string(guild_id, "game_key_offer_message", cost=cost, tacos_word=tacos_word),
                fields=fields,
                author=offered_by,
                view=claim_view,
            )

            # record offer
            self.db.open_game_key_offer(game_data["id"], guild_id, offer_message.id, ctx.channel.id)
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    async def _claim_offer_callback(self, interaction: discord.Interaction):
        _method = inspect.stack()[0][3]
        await interaction.response.defer()
        # create context from interaction
        ctx = self.discord_helper.create_context(
            self.bot,
            author=interaction.user,
            channel=interaction.channel,
            message=interaction.message,
            guild=interaction.guild,
            custom_id=interaction.data["custom_id"])
        self.log.debug(ctx.guild.id, f"{self._module}.{_method}", f"Claiming offer {interaction.data['custom_id']}")
        await self._claim_offer(ctx, interaction.data["custom_id"])
        await self._create_offer(ctx)


    async def _claim_timeout_callback(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        # create context from interaction
        ctx = self.discord_helper.create_context(
            self.bot,
            author=interaction.user,
            channel=interaction.channel,
            message=interaction.message,
            guild=interaction.guild
        )
        await self._create_offer(ctx)
        pass

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
            if not cog_settings:
                self.log.warn(guild_id, f"{self._module}.{_method}", f"No game_keys settings found for guild {guild_id}")
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, f"{self._module}.{_method}", f"game_keys is disabled for guild {guild_id}")
                return

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel: typing.Union[discord.TextChannel, None] = await self.discord_helper.get_or_fetch_channel(int(reward_channel_id))

            if not reward_channel:
                self.log.warn(guild_id, f"{self._module}.{_method}", f"No reward channel found for guild {guild_id}")
                return

            offer = self.db.find_open_game_key_offer(guild_id, reward_channel.id)
            if offer:
                try:
                    offer_message = await reward_channel.fetch_message(int(offer["message_id"]))
                    if offer_message:
                        try:
                            await offer_message.delete()
                        except Exception as e:
                            pass
                except discord.NotFound as nfe:
                    self.log.debug(guild_id, f"{self._module}.{_method}", f"Offer message not found for guild {guild_id}")
                    pass

                self.db.close_game_key_offer_by_message(guild_id, int(offer["message_id"]))

            else:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{_method}",
                    f"No open offer found for guild {guild_id} in channel {reward_channel.name}",
                )
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    async def _claim_offer(self, ctx, game_id: str) -> bool:
        _method = inspect.stack()[0][3]
        try:
            # claim the offer
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(guild_id, f"{self._module}.{_method}", f"No game_keys settings found for guild {guild_id}")
                return False
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, f"{self._module}.{_method}", f"game_keys is disabled for guild {guild_id}")
                return False

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel: typing.Union[discord.TextChannel, None] = await self.discord_helper.get_or_fetch_channel(int(reward_channel_id))
            log_channel_id = cog_settings.get("log_channel_id", "0")
            log_channel = await self.discord_helper.get_or_fetch_channel(int(log_channel_id))

            cost = cog_settings.get("cost", 500)
            if cost == 1:
                tacos_word = self.settings.get_string(guild_id, "taco_singular")
            else:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            # does the user have enough tacos?
            taco_count: int = self.db.get_tacos_count(guild_id, ctx.author.id)
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

            offer = self.db.find_open_game_key_offer(guild_id, reward_channel.id)
            game_data = None
            if offer:
                game_data = self.db.get_game_key_data(str(offer["game_key_id"]))
                if not game_data:
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{_method}",
                        f"No open offer found for game_key_id {offer['game_key_id']} in channel {reward_channel.name}",
                    )
                    return False
                if game_data["redeemed_by"] is not None:
                    # already redeemed
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{_method}",
                        f"Game key {game_data['id']} already redeemed by {game_data['redeemed_by']}",
                    )
                    await ctx.send(
                        self.settings.get_string(guild_id, "game_key_already_redeemed_message"), delete_after=10
                    )
                    return False
                if str(game_id) != str(offer["game_key_id"]) or str(game_data["_id"]) != str(game_id):
                    self.log.warn(
                        guild_id,
                        f"{self._module}.{_method}",
                        f"Requested game_id ('{str(game_id)}') with offer game_key_id ('{str(offer['game_key_id'])}') does not match offer game id '{str(game_data['_id'])}'",
                    )
                    return False
            else:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{_method}",
                    f"No offer found for channel {reward_channel.name} in guild {guild_id}",
                )
                return False
            if not game_data:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{_method}",
                    f"No game_key found while looking up id '{offer['game_key_id']}'",
                )
                await ctx.send(self.settings.get_string(guild_id, "game_key_no_game_data_message"), delete_after=10)
                return False

            # send them the game key
            if not game_data["key"]:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{_method}",
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
                    ),
                )
            except discord.Forbidden as f:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{_method}",
                    f"Unable to send game key for game '{game_data['title']}' ({game_id})",
                )
                await ctx.send(
                    self.settings.get_string(guild_id, "game_key_unable_to_send_message", user=ctx.author.mention),
                    delete_after=10,
                )
                return False
            # set the game as claimed
            self.db.claim_game_key_offer(game_id, ctx.author.id)
            # remove the tacos from the user
            self.db.remove_tacos(guild_id, ctx.author.id, cost)

            self.db.track_tacos_log(
                guildId=guild_id,
                fromUserId=ctx.author.id,
                toUserId=self.bot.user.id,
                count=cost * -1,
                reason="Claim game key",
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(tacotypes.TacoTypes.GAME_REDEEM)
            )

            # log that the offer was claimed
            if log_channel:
                await log_channel.send(
                    self.settings.get_string(
                        guild_id,
                        "game_key_claim_log_message",
                        user=f"{ctx.author.display_name}#{ctx.author.discriminator}",
                        game=game_data["title"],
                        tacos=cost,
                        tacos_word=tacos_word,
                    )
                )
            return True
        except Exception as e:
            raise e

    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings


async def setup(bot):
    await bot.add_cog(GameKeys(bot))
