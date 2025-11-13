# https://crafthead.net/armor/body/<uuid>
# https://playerdb.co/
# https://playerdb.co/api/player/minecraft/<name|uuid>

import inspect
import os
import traceback

import discord
import requests
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.helpers import ContextHelper, EntityHelper, MessageHelper, PromptHelper
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from discord.ext import commands
from discord.ext.commands import Context


class MinecraftCog(TacobotCog):
    # API endpoint constants for easier testing and configuration
    DEFAULT_MINECRAFT_API_BASE = "http://andeddu.bit13.local:10070"
    DEFAULT_PLAYER_DB_API = "https://playerdb.co/api/player/minecraft"
    DEFAULT_AVATAR_API = "https://crafthead.net/armor/body"

    def __init__(
        self,
        bot: TacoBot,
        minecraft_db: MinecraftDatabase,
        tracking_db: TrackingDatabase,
        messaging: MessageHelper,
        entity_helper: EntityHelper,
        context_helper: ContextHelper,
        prompt_helper: PromptHelper,
        settings: Settings,
        minecraft_api_base: str | None = None,
        player_db_api: str | None = None,
        avatar_api: str | None = None,
    ):
        super().__init__(bot, "minecraft", settings=settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.entity_helper = entity_helper
        self.context_helper = context_helper
        self.prompt_helper = prompt_helper

        self.messaging = messaging
        self.SELF_DESTRUCT_TIMEOUT = 30
        self.minecraft_db = minecraft_db
        self.tracking_db = tracking_db

        # API endpoints - configurable for testing
        self.minecraft_api_base = minecraft_api_base or self.DEFAULT_MINECRAFT_API_BASE
        self.player_db_api = player_db_api or self.DEFAULT_PLAYER_DB_API
        self.avatar_api = avatar_api or self.DEFAULT_AVATAR_API

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    # disable user from whitelist if they leave the discord
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        _method = inspect.stack()[0][3]
        try:
            guild_id = member.guild.id

            if not self._is_user_whitelisted(guild_id=guild_id, user_id=member.id):
                return
            mc_user = self.minecraft_db.get_minecraft_user(guildId=guild_id, userId=member.id)
            if not mc_user:
                return

            self.log.debug(
                member.guild.id, f"{self._module}.{self._class}.{_method}", f"Member {member.name} has left the server"
            )
            self.minecraft_db.whitelist_minecraft_user(
                guildId=guild_id, userId=member.id, username=mc_user['username'], uuid=mc_user['uuid'], whitelist=False
            )

        except Exception as e:
            self.log.error(member.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.group(name="minecraft", invoke_without_command=True)
    async def minecraft(self, ctx: Context):
        _method = inspect.stack()[0][3]
        if ctx.invoked_subcommand is not None:
            return
        guild_id = 0
        try:
            await self.status(ctx)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def status(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                await self._safe_delete_context_message(ctx)
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)

            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"minecraft is disabled for guild {guild_id}"
                )
                return

            # get the output channel from settings:
            output_channel, AUTO_DELETE_TIMEOUT = await self._determine_output_channel(ctx, cog_settings)
            self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"output_channel: {output_channel}")

            if not self._is_user_whitelisted(guild_id, ctx.author.id):
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                    message=self.settings.get_string(guild_id, "minecraft_not_whitelisted"),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            status = self._get_minecraft_status(guild_id)

            fields = self._build_status_fields(guild_id, status, cog_settings)

            await self.messaging.send_embed(
                channel=output_channel,
                title=self.settings.get_string(guild_id, "minecraft_status_server_status"),
                message=self.settings.get_string(
                    guild_id, "minecraft_status_message", title=status['title'], help=cog_settings['help']
                ),
                fields=fields,
                delete_after=AUTO_DELETE_TIMEOUT,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="minecraft",
                subcommand="status",
                args=[{"type": "command"}],
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @minecraft.command(name="start")
    @commands.guild_only()
    async def start_server(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                await self._safe_delete_context_message(ctx)
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)

            # get the output channel from settings:
            output_channel, AUTO_DELETE_TIMEOUT = await self._determine_output_channel(ctx, cog_settings)

            if not self._is_user_whitelisted(guild_id=guild_id, user_id=ctx.author.id):
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(guild_id, "minecraft_control_no_start"),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            status = self._get_minecraft_status(guild_id)

            if status['online']:
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(guild_id, "minecraft_control_running"),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} Started the Minecraft Server."
            )

            # send message to start the server
            resp = self._call_minecraft_start_api()
            if resp.status_code != 200:
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_control_start_failure_code", status_code=resp.status_code, action="start"
                    ),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return
            data = resp.json()
            if data['status'] != "success":
                self.log.error(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Failed to start the server: {data['message']}",
                )
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_control_failure", error=data['message'], action="start"
                    ),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            # notify the user that the server was started, and it will take a few minutes for it to be ready
            await self.messaging.send_embed(
                channel=output_channel,
                title=self.settings.get_string(guild_id, "minecraft_control_title"),
                message=self.settings.get_string(guild_id, "minecraft_control_start_success"),
                delete_after=AUTO_DELETE_TIMEOUT,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="minecraft",
                subcommand="start",
                args=[{"type": "command"}],
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @minecraft.command(name="stop")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def stop_server(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                await self._safe_delete_context_message(ctx)
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)

            # get the output channel from settings:
            output_channel, AUTO_DELETE_TIMEOUT = await self._determine_output_channel(ctx, cog_settings)

            status = self._get_minecraft_status(guild_id)

            if not status['online']:
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(guild_id, "minecraft_control_stopped"),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} Stopped the Minecraft Server."
            )

            # send message to stop the server
            resp = self._call_minecraft_stop_api()
            if resp.status_code != 200:
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_control_start_failure_code", status_code=resp.status_code, action="stop"
                    ),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return
            data = resp.json()
            if data['status'] != "success":
                self.log.error(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"Failed to stop the server: {data['message']}"
                )
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_control_failure", error=data['message'], action="stop"
                    ),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            # notify the user that the server was started, and it will take a few minutes for it to be ready
            await self.messaging.send_embed(
                channel=output_channel,
                title=self.settings.get_string(guild_id, "minecraft_control_title"),
                message=self.settings.get_string(guild_id, "minecraft_control_stop_success"),
                delete_after=AUTO_DELETE_TIMEOUT,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="minecraft",
                subcommand="stop",
                args=[{"type": "command"}],
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @minecraft.command()
    @commands.guild_only()
    async def whitelist(self, ctx: Context):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                await self._safe_delete_context_message(ctx)
                guild_id = ctx.guild.id

            if self._is_user_whitelisted(guild_id=guild_id, user_id=ctx.author.id):
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                    message=self.settings.get_string(guild_id, "minecraft_whitelist_already_whitelisted_message"),
                    delete_after=self.SELF_DESTRUCT_TIMEOUT,
                )
                return

            # try DM first
            try:
                _ctx = self.context_helper.create_context(
                    bot=self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild
                )
                mc_username = await self.prompt_helper.ask_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "minecraft_ask_username_title"),
                    self.settings.get_string(guild_id, "minecraft_ask_username_message"),
                    timeout=60 * 5,
                )
            except discord.Forbidden:
                _ctx = ctx
                mc_username = await self.prompt_helper.ask_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "minecraft_ask_username_title"),
                    self.settings.get_string(guild_id, "minecraft_ask_username_message"),
                    timeout=60 * 5,
                )

            if mc_username is None or mc_username.lower() == "cancel":
                return

            # cog_settings = self.get_cog_settings(guild_id)
            # if not cog_settings:
            #     self.log.warn(guild_id, "minecraft.whitelist", f"No minecraft settings found for guild {guild_id}")
            #     return
            # if not cog_settings.get("enabled", False):
            #     self.log.debug(guild_id, "minecraft.whitelist", f"minecraft is disabled for guild {guild_id}")
            #     return

            # {
            #     "code": "player.found",
            #     "message": "Successfully found player by given ID.",
            #     "data": {
            #         "player": {
            #             "meta": {
            #                 "name_history": [
            #                     {"name": "IcamalotI"},
            #                     {"name": "DarthMinos", "changedToAt": 1577518972000},
            #                 ]
            #             },
            #             "username": "DarthMinos",
            #             "id": "1b313cdd-7465-4227-95aa-ca5503beba85",
            #             "raw_id": "1b313cdd7465422795aaca5503beba85",
            #             "avatar": "https://crafthead.net/avatar/1b313cdd7465422795aaca5503beba85",
            #         }
            #     },
            #     "success": true,
            # }
            result = self._call_player_db_api(mc_username)
            if result.status_code != 200:
                # Need to notify of an error
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Failed to find player {mc_username}. (status_code: {result.status_code}) {result.text})",
                )
                await self.messaging.send_embed(
                    channel=_ctx.channel,
                    title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_whitelist_unable_to_verify", mc_username=mc_username
                    ),
                    color=0xFF0000,
                    delete_after=30,
                )
                return
                # raise Exception(f"Failed to find player {mc_username} from playerdb.co api call ({result.status_code} - {result.text})")

            data = result.json()

            # Process player data from API response
            player_info = self._process_player_data(data)
            if not player_info:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"Failed to find player {mc_username}"
                )
                await self.messaging.send_embed(
                    channel=_ctx.channel,
                    title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_whitelist_unable_to_verify", mc_username=mc_username
                    ),
                    color=0xFF0000,
                    delete_after=30,
                )
                return

            mc_uuid = player_info["uuid"]
            avatar_url = player_info["avatar_url"]

            # Build name history fields
            fields = []
            for n in player_info["name_history"]:
                fields.append({"name": "Name", "value": n["name"]})

            async def yes_no_callback(response: bool):
                if not response:
                    await self.messaging.send_embed(
                        channel=_ctx.channel,
                        title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                        message=self.settings.get_string(guild_id, "minecraft_whitelist_run_again"),
                        color=0xFF0000,
                        delete_after=20,
                    )
                else:
                    # if correct, add to whitelist
                    # check if user is in the whitelist
                    # minecraft_user = self.minecraft_db.get_minecraft_user(ctx.author.id)
                    self.minecraft_db.whitelist_minecraft_user(
                        guildId=guild_id, userId=ctx.author.id, username=mc_username, uuid=mc_uuid, whitelist=True
                    )
                    await self.messaging.send_embed(
                        channel=_ctx.channel,
                        title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                        message=self.settings.get_string(
                            guild_id,
                            "minecraft_whitelist_message",
                            username=mc_username,
                            uuid=mc_uuid,
                            server="mc.fuku.io",
                            modpack="All The Mods 7 v0.4.0",
                        ),
                        color=0x00FF00,
                        delete_after=30,
                    )

            await self.prompt_helper.ask_yes_no(
                _ctx,
                _ctx.channel,
                title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                question=self.settings.get_string(
                    guild_id, "minecraft_whitelist_account_verify", mc_username=mc_username
                ),
                fields=fields,
                image=avatar_url,
                result_callback=yes_no_callback,
            )

            # if correct, add to whitelist
            # check if user is in the whitelist
            # minecraft_user = self.minecraft_db.get_minecraft_user(ctx.author.id)
            self.minecraft_db.whitelist_minecraft_user(
                guildId=guild_id, userId=ctx.author.id, username=mc_username, uuid=mc_uuid, whitelist=True
            )
            await self.messaging.send_embed(
                channel=_ctx.channel,
                title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                message=self.settings.get_string(
                    guild_id, "minecraft_whitelist_success_message", mc_username=mc_username, mc_uuid=mc_uuid
                ),
                color=0x00FF00,
                delete_after=30,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="minecraft",
                subcommand="whitelist",
                args=[{"type": "command"}],
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    def _clean_username(self, username: str) -> str:
        return username.strip().lower()

    def _process_player_data(self, api_response_data: dict) -> dict | None:
        """Process the PlayerDB API response and extract player information.

        Args:
            api_response_data: JSON data from PlayerDB API response

        Returns:
            Dictionary containing player info (uuid, raw_id, username, name_history, avatar_url)
            or None if player data is invalid
        """
        if not api_response_data.get("success") or api_response_data.get("code") != "player.found":
            return None

        player_data = api_response_data.get("data", {}).get("player", {})
        if not player_data:
            return None

        mc_uuid = player_data.get("id")
        mc_raw_id = player_data.get("raw_id")
        mc_username = player_data.get("username")
        name_history = player_data.get("meta", {}).get("name_history", [])

        if not mc_uuid or not mc_raw_id:
            return None

        avatar_url = f"{self.avatar_api}/{mc_raw_id}"

        return {
            "uuid": mc_uuid,
            "raw_id": mc_raw_id,
            "username": mc_username,
            "name_history": name_history,
            "avatar_url": avatar_url,
        }

    def _call_minecraft_start_api(self) -> requests.Response:
        """Call the Minecraft server start API endpoint.

        Returns:
            Response object from the API call
        """
        start_url = f"{self.minecraft_api_base}/taco/minecraft/server/start"
        return requests.post(start_url)

    def _call_minecraft_stop_api(self) -> requests.Response:
        """Call the Minecraft server stop API endpoint.

        Returns:
            Response object from the API call
        """
        stop_url = f"{self.minecraft_api_base}/taco/minecraft/server/stop"
        return requests.post(stop_url)

    def _call_player_db_api(self, username: str) -> requests.Response:
        """Look up a Minecraft player by username using the PlayerDB API.

        Args:
            username: Minecraft username to look up (will be cleaned)

        Returns:
            Response object from the API call
        """
        clean_username = self._clean_username(username)
        player_url = f"{self.player_db_api}/{clean_username}"
        return requests.get(player_url)

    def _call_minecraft_status_api(self) -> requests.Response:
        """Get the current Minecraft server status.

        Returns:
            Response object from the API call
        """
        status_url = f"{self.minecraft_api_base}/tacobot/minecraft/status"
        return requests.get(status_url)

    async def _determine_output_channel(self, ctx: Context, cog_settings: dict) -> tuple:
        """Determine the appropriate output channel and timeout for a command.

        Args:
            ctx: Discord command context
            cog_settings: Cog settings dictionary

        Returns:
            Tuple of (output_channel, auto_delete_timeout)
        """
        AUTO_DELETE_TIMEOUT = self.SELF_DESTRUCT_TIMEOUT
        output_channel = await self.entity_helper.get_or_fetch_channel(int(cog_settings.get("output_channel", 0)))

        if not output_channel or output_channel.id != ctx.channel.id:
            output_channel = ctx.author
            AUTO_DELETE_TIMEOUT = None

        return output_channel, AUTO_DELETE_TIMEOUT

    async def _safe_delete_context_message(self, ctx: Context) -> bool:
        """Safely attempt to delete the context message.

        Args:
            ctx: Discord command context

        Returns:
            True if deletion succeeded or message doesn't exist, False if deletion failed
        """
        if not ctx.message:
            return True

        try:
            await ctx.message.delete()
            return True
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            # Message already deleted, no permissions, or other Discord error
            return False

    def _build_status_fields(self, guild_id: int, status: dict, cog_settings: dict) -> list[dict]:
        """Build the status embed fields for the Minecraft server status display.

        Args:
            guild_id: Discord guild ID for localized strings
            status: Server status data from the API
            cog_settings: Cog configuration settings

        Returns:
            List of embed field dictionaries
        """
        fields = [
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_host"),
                "value": f"`{cog_settings['server']}`",
                "inline": False,
            },
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_players_slots"),
                "value": f"{status['players']['online']}/{status['players']['max']}",
                "inline": False,
            },
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_version"),
                "value": f"{status['version']}",
                "inline": False,
            },
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_forge_version"),
                "value": f"{cog_settings['forge_version']}",
                "inline": False,
            },
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_mods"),
                "value": "------------------",
                "inline": False,
            },
        ]

        if not status['online']:
            fields.append(
                {
                    "name": self.settings.get_string(guild_id, "minecraft_status_server_status"),
                    "value": "Server is offline. Run `.taco minecraft start` to start the server.",
                    "inline": False,
                }
            )

        for m in cog_settings["mods"]:
            fields.append({"name": f"{m['name']}", "value": f"{m['version']}", "inline": True})

        return fields

    def _is_user_whitelisted(self, guild_id: int, user_id: int):
        # check if user is in the whitelist
        minecraft_user = self.minecraft_db.get_minecraft_user(guildId=guild_id, userId=user_id)
        if not minecraft_user:
            return False

        # check if user is whitelisted
        if not minecraft_user["whitelist"]:
            return False

        return True

    def _get_minecraft_status(self, guild_id: int = 0) -> dict:
        _method = inspect.stack()[0][3]
        result = self._call_minecraft_status_api()
        if result.status_code != 200:
            # Need to notify of an error
            self.log.warn(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Failed to get minecraft status ({result.status_code} - {result.text})",
            )
            raise Exception(f"Failed to get minecraft status ({result.status_code} - {result.text})")

        data = result.json()
        # get users uuid for minecraft username
        if not data["success"]:
            self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", "Failed to get minecraft status")
        return data


async def setup(bot):
    settings = Settings()
    minecraft_db = MinecraftDatabase()
    tracking_db = TrackingDatabase()
    messaging = MessageHelper(bot, settings)
    entity_helper = EntityHelper(bot)
    context_helper = ContextHelper()
    prompt_helper = PromptHelper(bot, settings, messaging)
    await bot.add_cog(
        MinecraftCog(
            bot=bot,
            settings=settings,
            minecraft_db=minecraft_db,
            tracking_db=tracking_db,
            messaging=messaging,
            entity_helper=entity_helper,
            context_helper=context_helper,
            prompt_helper=prompt_helper,
        )
    )
