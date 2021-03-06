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
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import (
    create_button,
    create_actionrow,
    create_select,
    create_select_option,
    wait_for_component,
)
from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider


class GameKeys(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "game_keys"
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "game_keys.__init__", "Initialized")

    @commands.group(name="game-keys")
    @commands.guild_only()
    async def game_keys(self, ctx):
        pass

    @game_keys.command(name="open")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def open(self, ctx) -> None:
        try:
            await ctx.message.delete()
            await self._create_offer(ctx)
        except Exception as e:
            self.log.error(ctx.guild.id, "game_keys.open", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @game_keys.command(name="close")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def close(self, ctx):
        try:
            await ctx.message.delete()
            await self._close_offer(ctx)
        except Exception as e:
            self.log.error(ctx.guild.id, "game_keys.close", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)


    # @commands.Cog.listener()
    # async def on_component(self, ctx: ComponentContext):
    #     self.log.debug(ctx.guild.id, "game_keys.on_component", f"Received component {ctx.component_name}")
    #     await ctx.defer(
    #         ignore=True
    #     )  # ignore, i.e. don't do anything *with the button* when it's pressed.
    #     pass

    async def _create_offer(self, ctx) -> None:
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            # if there is an existing offer, close it
            # then create a new offer
            await self._close_offer(ctx)

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(guild_id, "game_keys._create_offer", f"No game_keys settings found for guild {guild_id}")
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, "game_keys._create_offer", f"game_keys is disabled for guild {guild_id}")
                return

            cost = cog_settings.get("cost", 500)
            if cost <= 0:
                self.log.warn(guild_id, "game_keys._create_offer", f"Cost is 0 or less for guild {guild_id}")
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
                self.log.warn(guild_id, "game_keys._create_offer", f"No reward channel found for guild {guild_id}")
                return
            if not log_channel:
                self.log.warn(guild_id, "game_keys._create_offer", f"No log channel found for guild {guild_id}")
                return

            game_data = self.db.get_random_game_key_data()
            if not game_data:
                await ctx.send(self.settings.get_string(guild_id, "game_key_no_keys_found_message"), delete_after=10)
                return

            offered_by = await self.bot.fetch_user(int(game_data["offered_by"]))
            expires = datetime.datetime.now() + datetime.timedelta(days=1)
            fields = [
                {"name": self.settings.get_string(guild_id, "game"), "value": game_data.get("title", "UNKNOWN")},
                {"name": self.settings.get_string(guild_id, "platform"), "value": game_data.get("platform", "UNKNOWN")},
                {"name": self.settings.get_string(guild_id, "cost"), "value": f"{cost} {tacos_word}????"},
                {
                    "name": self.settings.get_string(guild_id, "link"),
                    "value": game_data.get("info_url", "[Unavailable]"),
                },
                {
                    "name": self.settings.get_string(guild_id, "expires"),
                    "value": f"{expires.strftime('%Y-%m-%d %H:%M:%S')} UTC",
                },
            ]

            buttons = [
                create_button(
                    style=ButtonStyle.green,
                    label=self.settings.get_string(
                        ctx.guild.id, "game_key_claim_button", tacos=cost, tacos_word=tacos_word
                    ),
                    # custom_id="CLAIM",
                    custom_id=str(game_data["id"]),
                ),
            ]
            action_row = create_actionrow(*buttons)

            offer_message = await self.discord_helper.sendEmbed(
                reward_channel,
                self.settings.get_string(guild_id, "game_key_offer_title"),
                self.settings.get_string(guild_id, "game_key_offer_message", cost=cost, tacos_word=tacos_word),
                fields=fields,
                author=offered_by,
                components=[action_row],
            )
            # record offer
            self.db.open_game_key_offer(game_data["id"], guild_id, offer_message.id, ctx.channel.id)
            timeout = 60 * 60 * 24
            try:
                button_ctx: ComponentContext = await wait_for_component(
                    self.bot, components=action_row, timeout=timeout
                )
                await button_ctx.defer(ignore=True)
            except asyncio.TimeoutError:
                try:
                    self.log.debug(guild_id, "game_keys._create_offer", f"Timeout waiting for claim button press.")
                    await self._create_offer(ctx)
                except Exception as e:
                    self.log.error(ctx.guild.id, "game_keys._create_offer", str(e), traceback.format_exc())
            else:
                new_ctx = self.discord_helper.create_context(self.bot, author=button_ctx.author, channel=ctx.channel, message=ctx.message, guild=ctx.guild, custom_id=button_ctx.custom_id)
                claimed = await self._claim_offer(new_ctx, game_data.get("id", None))
                if claimed:
                    self.log.debug(guild_id, "game_keys._create_offer", f"Claimed offer for id {button_ctx.custom_id}")
                    await self._create_offer(ctx)
                else:
                    self.log.debug(guild_id, "game_keys._create_offer", f"Failed to claim offer for id {button_ctx.custom_id}")
                    # check if expired offer.
        except Exception as e:
            self.log.error(ctx.guild.id, "game_keys._create_offer", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    # async def _wait_or_new_offer(self, ctx):
    #     try:
    #         await asyncio.wait_for(self.eternity(), timeout=1.0)
    #     except asyncio.TimeoutError:
    #         await self._create_offer(ctx)
    # async def eternity(self):
    #     # Sleep for 2 days
    #     await asyncio.sleep((60 * 60 * 24) * 2)

    async def _close_offer(self, ctx) -> None:
        # get the current offer and close it
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(guild_id, "game_keys._create_offer", f"No game_keys settings found for guild {guild_id}")
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, "game_keys._create_offer", f"game_keys is disabled for guild {guild_id}")
                return

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel: discord.TextChannel = await self.discord_helper.get_or_fetch_channel(int(reward_channel_id))

            if not reward_channel:
                self.log.warn(guild_id, "game_keys._create_offer", f"No reward channel found for guild {guild_id}")
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
                    self.log.debug(guild_id, "game_keys._create_offer", f"Offer message not found for guild {guild_id}")
                    pass

                self.db.close_game_key_offer_by_message(guild_id, int(offer["message_id"]))

            else:
                self.log.debug(
                    guild_id,
                    "game_keys._close_offer",
                    f"No open offer found for guild {guild_id} in channel {reward_channel.name}",
                )
        except Exception as e:
            self.log.error(ctx.guild.id, "game_keys._close_offer", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    async def _claim_offer(self, ctx, game_id: str) -> bool:
        try:
            # claim the offer
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(guild_id, "game_keys._create_offer", f"No game_keys settings found for guild {guild_id}")
                return False
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, "game_keys._create_offer", f"game_keys is disabled for guild {guild_id}")
                return False

            reward_channel_id = cog_settings.get("reward_channel_id", "0")
            reward_channel: discord.TextChannel = await self.discord_helper.get_or_fetch_channel(int(reward_channel_id))
            log_channel_id = cog_settings.get("log_channel_id", "0")
            log_channel = await self.discord_helper.get_or_fetch_channel(int(log_channel_id))

            cost = cog_settings.get("cost", 500)
            if cost == 1:
                tacos_word = self.settings.get_string(guild_id, "taco_singular")
            else:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            # does the user have enough tacos?
            taco_count = self.db.get_tacos_count(guild_id, ctx.author.id)
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
                        "game_keys._claim_offer",
                        f"No open offer found for game_key_id {offer['game_key_id']} in channel {reward_channel.name}",
                    )
                    return False
                if game_data["redeemed_by"] is not None:
                    # already redeemed
                    self.log.debug(
                        guild_id,
                        "game_keys._claim_offer",
                        f"Game key {game_data['id']} already redeemed by {game_data['redeemed_by']}",
                    )
                    await ctx.send(
                        self.settings.get_string(guild_id, "game_key_already_redeemed_message"), delete_after=10
                    )
                    return False
                if str(game_id) != str(offer["game_key_id"]) or str(game_data["_id"]) != str(game_id):
                    self.log.warn(
                        guild_id,
                        "game_keys._claim_offer",
                        f"Requested game_id ('{str(game_id)}') with offer game_key_id ('{str(offer['game_key_id'])}') does not match offer game id '{str(game_data['_id'])}'",
                    )
                    return False
            else:
                self.log.warn(
                    guild_id,
                    "game_keys._claim_offer",
                    f"No offer found for channel {reward_channel.name} in guild {guild_id}",
                )
                return False
            if not game_data:
                self.log.warn(
                    guild_id,
                    "game_keys._claim_offer",
                    f"No game_key found while looking up id '{offer['game_key_id']}'",
                )
                await ctx.send(self.settings.get_string(guild_id, "game_key_no_game_data_message"), delete_after=10)
                return False

            # send them the game key
            if not game_data["key"]:
                self.log.warn(
                    guild_id,
                    "game_keys._claim_offer",
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
                    "game_keys._claim_offer",
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

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No game_key settings found for guild {guildId}")
        return cog_settings


def setup(bot):
    bot.add_cog(GameKeys(bot))
