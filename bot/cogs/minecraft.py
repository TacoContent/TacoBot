# https://crafthead.net/armor/body/<uuid>
# https://playerdb.co/
# https://playerdb.co/api/player/minecraft/<name|uuid>

import inspect
import os
import traceback

import discord
import requests
from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.messaging import Messaging
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from discord.ext import commands
from discord.ext.commands import Context


class MinecraftCog(TacobotCog):
    def __init__(self, bot):
        super().__init__(bot, "minecraft")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.SELF_DESTRUCT_TIMEOUT = 30
        self.minecraft_db = MinecraftDatabase()
        self.tracking_db = TrackingDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    # disable user from whitelist if they leave the discord
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        _method = inspect.stack()[0][3]
        try:
            guild_id = member.guild.id

            if not self.is_user_whitelisted(guild_id=guild_id, user_id=member.id):
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
                await ctx.message.delete()
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)

            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"minecraft is disabled for guild {guild_id}"
                )
                return

            # get the output channel from settings:
            AUTO_DELETE_TIMEOUT = self.SELF_DESTRUCT_TIMEOUT
            output_channel = await self.discord_helper.get_or_fetch_channel(int(cog_settings.get("output_channel", 0)))
            self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"output_channel: {output_channel}")
            if not output_channel or output_channel.id != ctx.channel.id:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"output_channel is not set or is not the same as the command channel",
                )
                output_channel = ctx.author
                AUTO_DELETE_TIMEOUT = None

            if not self.is_user_whitelisted(guild_id, ctx.author.id):
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                    message=self.settings.get_string(guild_id, "minecraft_not_whitelisted"),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            status = self.get_minecraft_status(guild_id)

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
                    "value": f"------------------",
                    "inline": False,
                },
            ]

            if status['online'] == False:
                # add field to tell user how to start the server

                fields.append(
                    {
                        "name": self.settings.get_string(guild_id, "minecraft_status_server_status"),
                        "value": f"Server is offline. Run `.taco minecraft start` to start the server.",
                        "inline": False,
                    }
                )

            for m in cog_settings["mods"]:
                fields.append({"name": f"{m['name']}", "value": f"{m['version']}", "inline": True})

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
                await ctx.message.delete()
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)

            # get the output channel from settings:
            AUTO_DELETE_TIMEOUT = self.SELF_DESTRUCT_TIMEOUT
            output_channel = await self.discord_helper.get_or_fetch_channel(int(cog_settings.get("output_channel", 0)))
            if not output_channel or output_channel.id != ctx.channel.id:
                output_channel = ctx.author
                AUTO_DELETE_TIMEOUT = None

            if not self.is_user_whitelisted(guild_id=guild_id, user_id=ctx.author.id):
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(guild_id, "minecraft_control_no_start"),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            status = self.get_minecraft_status(guild_id)

            if status['online'] == True:
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
            # TODO: store url in settings
            resp = requests.post(f"http://andeddu.bit13.local:10070/taco/minecraft/server/start")
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
                await ctx.message.delete()
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)

            # get the output channel from settings:
            AUTO_DELETE_TIMEOUT = self.SELF_DESTRUCT_TIMEOUT
            output_channel = await self.discord_helper.get_or_fetch_channel(int(cog_settings.get("output_channel", 0)))
            if not output_channel or output_channel.id != ctx.channel.id:
                output_channel = ctx.author
                AUTO_DELETE_TIMEOUT = None

            status = self.get_minecraft_status(guild_id)

            if status['online'] == False:
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
            # TODO: store url in settings
            resp = requests.post(f"http://andeddu.bit13.local:10070/taco/minecraft/server/stop")
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
                await ctx.message.delete()
                guild_id = ctx.guild.id

            if self.is_user_whitelisted(guild_id=guild_id, user_id=ctx.author.id):
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                    message=self.settings.get_string(guild_id, "minecraft_whitelist_already_whitelisted_message"),
                    delete_after=self.SELF_DESTRUCT_TIMEOUT,
                )
                return

            # try DM first
            try:
                _ctx = self.discord_helper.create_context(
                    self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild
                )
                mc_username = await self.discord_helper.ask_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "minecraft_ask_username_title"),
                    self.settings.get_string(guild_id, "minecraft_ask_username_message"),
                    timeout=60 * 5,
                )
            except discord.Forbidden:
                _ctx = ctx
                mc_username = await self.discord_helper.ask_text(
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
            # TODO: store url in settings
            result = requests.get(f"https://playerdb.co/api/player/minecraft/{mc_username}")
            if result.status_code != 200:
                # Need to notify of an error
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
                # raise Exception(f"Failed to find player {mc_username} from playerdb.co api call ({result.status_code} - {result.text})")

            data = result.json()
            # get users uuid for minecraft username
            if not data["success"] or data["code"] != "player.found":
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

            # get user avatar for minecraft uuid
            mc_uuid = data["data"]["player"]["id"]
            mc_raw_id = data["data"]["player"]["raw_id"]

            # ask user if the avatar looks correct
            # https://crafthead.net/armor/body/{uuid}
            # TODO: store url in settings
            avatar_url = f"https://crafthead.net/armor/body/{mc_raw_id}"
            fields = []
            for n in data["data"]["player"]["name_history"]:
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

            await self.discord_helper.ask_yes_no(
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

    def is_user_whitelisted(self, guild_id: int, user_id: int):
        # check if user is in the whitelist
        minecraft_user = self.minecraft_db.get_minecraft_user(guildId=guild_id, userId=user_id)
        if not minecraft_user:
            return False

        # check if user is whitelisted
        if not minecraft_user["whitelist"]:
            return False

        return True

    def get_minecraft_status(self, guild_id: int = 0) -> dict:
        _method = inspect.stack()[0][3]
        # TODO: store url in settings
        result = requests.get(f"http://andeddu.bit13.local:10070/tacobot/minecraft/status")
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
            self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", f"Failed to get minecraft status")
        return data


async def setup(bot):
    await bot.add_cog(MinecraftCog(bot))
