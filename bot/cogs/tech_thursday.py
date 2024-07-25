import datetime
import inspect
import os
import traceback
import typing

import discord
from bot.lib import discordhelper, logger, settings, utils
from bot.lib.enums import loglevel, tacotypes
from bot.lib.messaging import Messaging
from bot.lib.mongodb.techthurs import TechThursDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.permissions import Permissions
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from openai import OpenAI


class TechThursdays(commands.Cog):
    group = app_commands.Group(name="techthurs", description="Commands for the Tech Thursdays")

    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.permissions = Permissions(bot)
        self.SETTINGS_SECTION = "techthurs"
        self.SELF_DESTRUCT_TIMEOUT = 30

        self.techthurs_db = TechThursDatabase()
        self.tracking_db = TrackingDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.group(name="techthurs", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def techthurs(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        if ctx.invoked_subcommand is not None:
            return
        guild_id = 0
        try:
            await ctx.message.delete()
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            # needs to accept an image along with the text
            try:
                _ctx = self.discord_helper.create_context(
                    self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild
                )
                twa = await self.discord_helper.ask_for_image_or_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "techthurs_ask_title"),
                    self.settings.get_string(guild_id, "techthurs_ask_message"),
                    timeout=60 * 5,
                )
            except discord.Forbidden:
                _ctx = ctx
                twa = await self.discord_helper.ask_for_image_or_text(
                    _ctx,
                    ctx.author,
                    self.settings.get_string(guild_id, "techthurs_ask_title"),
                    self.settings.get_string(guild_id, "techthurs_ask_message"),
                    timeout=60 * 5,
                )

            # ask the user for the techthurs in DM
            if twa is None or twa.text.lower() == "cancel":
                return

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"techthurs is disabled for guild {guild_id}"
                )
                return

            tacos_settings = self.get_tacos_settings(guild_id)

            amount = tacos_settings.get("techthurs_amount", 5)

            role_tag = None
            role = ctx.guild.get_role(int(cog_settings.get("tag_role", 0)))
            if role:
                role_tag = f"{role.mention}"

            message_content = None
            # if twa.text is not None and twa.text != "":
            #     if role_tag is not None:
            #         message_content = f"{role_tag}"
            #     else:
            #         message_content = ""
            # else:
            #     if role_tag is not None:
            #         message_content = role_tag

            if role_tag is not None:
                message_content = role_tag

            out_channel = ctx.guild.get_channel(int(cog_settings.get("output_channel_id", 0)))
            if not out_channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}"
                )

            # get role
            taco_word = self.settings.get_string(guild_id, "taco_singular")
            if amount != 1:
                taco_word = self.settings.get_string(guild_id, "taco_plural")
            out_message = self.settings.get_string(
                guildId=guild_id, key="techthurs_out_message", taco_count=amount, taco_word=taco_word, message=twa.text
            )
            techthurs_message = await self.messaging.send_embed(
                channel=out_channel,
                title=self.settings.get_string(guild_id, "techthurs_out_title"),
                message=out_message,
                content=message_content,
                color=0x00FF00,
                image=twa.attachments[0].url,
                thumbnail=None,
                footer=None,
                author=None,
                fields=None,
                delete_after=None,
            )

            # save the techthurs to the database
            self.techthurs_db.save_techthurs(
                guildId=guild_id,
                message=twa.text,
                image=twa.attachments[0].url,
                author=ctx.author.id,
                channel_id=out_channel.id,
                message_id=techthurs_message.id,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="techthurs",
                subcommand=None,
                args=[{"type": "command"}, {"message_id": str(techthurs_message.id)}],
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @group.command(name="ai", description="Generate a question using AI")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def openai_app_command(self, ctx: discord.Interaction) -> None:
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if not utils.isAdmin(ctx, self.settings):
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"User is not an admin ({ctx.user}). Command: ({ctx.command})",
                )
                await ctx.response.send_message(content="You must be a bot admin to use this command", ephemeral=True)
                return

            if ctx.guild:
                guild_id = ctx.guild.id
            else:
                self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", "No guild found for context")
                return
            await self._openai_generate(ctx)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.user.id,
                command="techthurs",
                subcommand="ai",
                args=[{"type": "slash_command"}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @techthurs.command(name="openai", aliases=["ai"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def openai(self, ctx: Context):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.message:
                await ctx.message.delete()

            await self._openai_generate(ctx)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="tqotd",
                subcommand="openai",
                args=[{"type": "command"}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @techthurs.command(name="import")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def import_techthurs(self, ctx, message_id: int) -> None:
        """Import techthurs from an existing post"""
        _method = inspect.stack()[0][3]
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        try:
            await ctx.message.delete()

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No techthurs settings found for guild {guild_id}",
                )
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"techthurs is disabled for guild {guild_id}"
                )
                return

            out_channel = ctx.guild.get_channel(int(cog_settings.get("output_channel_id", 0)))
            if not out_channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}"
                )

            # get the message from the id
            message = await out_channel.fetch_message(message_id)
            if not message:
                return

            self._import_techthurs(message)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="techthurs",
                subcommand="import",
                args=[{"type": "command"}, {"message_id": str(message.id)}],
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @techthurs.command(name="give")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def give(self, ctx, member: discord.Member) -> None:
        _method = inspect.stack()[0][3]
        try:
            await ctx.message.delete()

            await self.give_user_techthurs_tacos(ctx.guild.id, member.id, ctx.channel.id, None)

            self.tracking_db.track_command_usage(
                guildId=ctx.guild.id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="techthurs",
                subcommand="give",
                args=[{"type": "command"}, {"member_id": str(member.id)}],
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def _on_raw_reaction_add_give(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id

        # check if the user that reacted is in the admin role
        if not await self.permissions.is_admin(payload.user_id, guild_id):
            self.log.debug(
                guild_id, f"{self._module}.{self._class}.{_method}", f"User {payload.user_id} is not an admin"
            )
            return
        # in future, check if the user is in a defined role that can grant tacos (e.g. moderator)

        # get the message that was reacted to
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        message_author = message.author
        react_user = await self.discord_helper.get_or_fetch_user(payload.user_id)

        if not react_user or react_user.bot or react_user.system:
            return

        # check if this reaction is the first one of this type on the message
        reactions = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        if reactions and reactions.count > 1:
            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}",
            )
            return

        already_tracked = self.techthurs_db.techthurs_user_message_tracked(guild_id, message_author.id, message.id)
        if not already_tracked:
            # log that we are giving tacos for this reaction
            self.log.info(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"User {payload.user_id} reacted with {payload.emoji.name} to message {payload.message_id}",
            )
            await self.give_user_techthurs_tacos(guild_id, message_author.id, payload.channel_id, payload.message_id)

            self.tracking_db.track_command_usage(
                guildId=payload.guild_id,
                channelId=payload.channel_id if payload.channel_id else None,
                userId=payload.user_id,
                command="techthurs",
                subcommand="give",
                args=[
                    {"type": "reaction"},
                    {
                        "payload": {
                            "message_id": str(payload.message_id),
                            "channel_id": str(payload.channel_id),
                            "guild_id": str(payload.guild_id),
                            "user_id": str(payload.user_id),
                            "emoji": payload.emoji.name,
                            "event_type": payload.event_type,
                            # "burst": payload.burst,
                        }
                    },
                ],
            )
        else:
            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Message {payload.message_id} has already been tracked for techthurs. Skipping.",
            )

    async def _on_raw_reaction_add_import(self, payload) -> None:
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id

        # check if the user that reacted is in the admin role
        if not await self.permissions.is_admin(payload.user_id, guild_id):
            self.log.debug(
                guild_id, f"{self._module}.{self._class}.{_method}", f"User {payload.user_id} is not an admin"
            )
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        # check if this reaction is the first one of this type on the message
        reactions = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        if reactions and reactions.count > 1:
            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}",
            )
            return

        self._import_techthurs(message)

        self.tracking_db.track_command_usage(
            guildId=payload.guild_id,
            channelId=payload.channel_id if payload.channel_id else None,
            userId=payload.user_id,
            command="techthurs",
            subcommand="import",
            args=[
                {"type": "reaction"},
                {
                    "payload": {
                        "message_id": str(payload.message_id),
                        "channel_id": str(payload.channel_id),
                        "guild_id": str(payload.guild_id),
                        "user_id": str(payload.user_id),
                        "emoji": payload.emoji.name,
                        "event_type": payload.event_type,
                        # "burst": payload.burst,
                    }
                },
            ],
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:
            if payload.event_type != "REACTION_ADD":
                return

            # check if the user that reacted is in the admin role
            if not await self.permissions.is_admin(payload.user_id, guild_id):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"User {payload.user_id} is not an admin"
                )
                return

            react_user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if not react_user or react_user.bot or react_user.system:
                return

            cog_settings = self.get_cog_settings(guild_id)

            reaction_emojis = cog_settings.get("reaction_emoji", ["💻"])
            reaction_import_emojis = cog_settings.get("import_emoji", ["🇮"])
            check_list = reaction_emojis + reaction_import_emojis
            if str(payload.emoji.name) not in check_list:
                return

            if str(payload.emoji.name) in reaction_emojis:
                await self._on_raw_reaction_add_give(payload)
                return

            # is today thursday?
            today = datetime.datetime.now()
            if today.weekday() != 3:  # 0 = Monday, 1=Tuesday, 2=Wednesday...
                return
            if str(payload.emoji.name) in reaction_import_emojis:
                await self._on_raw_reaction_add_import(payload)
                return

        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            # await self.messaging.notify_of_error(ctx)

    def _import_techthurs(self, message: discord.Message) -> None:
        _method = inspect.stack()[0][3]
        guild_id = message.guild.id
        channel_id = message.channel.id
        message_id = message.id
        message_author = message.author
        message_content = message.content

        # get the image
        image_url = None
        if message.attachments is not None and len(message.attachments) > 0:
            image_url = message.attachments[0].url

        # get the text
        text = None
        if message_content is not None and message_content != "":
            text = message_content

        self.log.debug(
            guild_id,
            f"{self._module}.{self._class}.{_method}",
            f"Importing techthurs message {message_id} from channel {channel_id} in guild {guild_id} for user {message_author.id} with text {text} and image {image_url}",
        )
        self.techthurs_db.save_techthurs(
            guildId=guild_id,
            message=text or "",
            image=image_url,
            author=message_author.id,
            channel_id=channel_id,
            message_id=message_id,
        )

    async def give_user_techthurs_tacos(self, guild_id, user_id, channel_id, message_id) -> None:
        _method = inspect.stack()[0][3]
        try:
            # create context
            # self, bot=None, author=None, guild=None, channel=None, message=None, invoked_subcommand=None, **kwargs
            # get guild from id
            guild = self.bot.get_guild(guild_id)
            # fetch member from id
            member = guild.get_member(user_id)
            # get channel
            channel = None
            if channel_id:
                channel = self.bot.get_channel(channel_id)
            else:
                channel = guild.system_channel
            if not channel:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}"
                )
                return
            message = None
            # get message
            if message_id and channel:
                message = await channel.fetch_message(message_id)

            # get bot
            bot = self.bot
            ctx = self.discord_helper.create_context(
                bot=bot, guild=guild, author=member, channel=channel, message=message
            )

            # track that the user answered the question.
            self.techthurs_db.track_techthurs_answer(guild_id, member.id, message_id)

            tacos_settings = self.get_tacos_settings(guild_id)
            amount = tacos_settings.get("tech_thursday_count", 5)

            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reason_msg = self.settings.get_string(guild_id, "techthurs_reason_default")

            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "taco_give_title"),
                # 	"taco_gift_success": "{{user}}, You gave {touser} {amount} {taco_word} 🌮.\n\n{{reason}}",
                message=self.settings.get_string(
                    guild_id,
                    "taco_gift_success",
                    user=self.bot.user,
                    touser=member.mention,
                    amount=amount,
                    taco_word=tacos_word,
                    reason=reason_msg,
                ),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=self.SELF_DESTRUCT_TIMEOUT),
                delete_after=self.SELF_DESTRUCT_TIMEOUT,
            )

            await self.discord_helper.taco_give_user(
                guild_id, self.bot.user, member, reason_msg, tacotypes.TacoTypes.TECH_THURSDAY, taco_amount=amount
            )

        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def _openai_generate(self, ctx: typing.Union[Context, discord.Interaction]) -> None:
        _method = inspect.stack()[0][3]
        guild_id = 0

        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", "No guild found for context")
            return
        user: typing.Optional[typing.Union[discord.Member, discord.User]] = None
        if ctx and hasattr(ctx, "author"):
            user = ctx.author
        elif ctx and hasattr(ctx, "user"):
            user = ctx.user
        else:
            self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", "No user found for context")
            return

        cog_settings = self.get_cog_settings(guild_id)
        if not cog_settings.get("enabled", False):
            self.log.debug(
                guild_id, f"{self._module}.{self._class}.{_method}", f"techthurs is disabled for guild {guild_id}"
            )
            return

        tacos_settings = self.get_tacos_settings(guild_id)

        amount = tacos_settings.get("techthurs_amount", 5)

        message_content = ""
        role = await self.discord_helper.get_or_fetch_role(ctx.guild, int(cog_settings.get("tag_role", 0)))
        if role:
            message_content = f"{role.mention}"

        out_channel = await self.discord_helper.get_or_fetch_channel(int(cog_settings.get("output_channel_id", 0)))
        if not out_channel:
            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}"
            )
            out_channel = ctx.channel

        if not out_channel:
            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", f"No output channel found for guild {guild_id}"
            )
            return

        # get role
        taco_word = self.settings.get_string(guild_id, "taco_singular")
        if amount != 1:
            taco_word = self.settings.get_string(guild_id, "taco_plural")
        ai_settings = cog_settings.get("ai", {})
        ai_prompt = ai_settings.get("prompt", {})

        openai = OpenAI()
        airesponse = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": utils.str_replace(ai_prompt.get("system", ""))},
                {"role": "user", "content": utils.str_replace(ai_prompt.get("user", ""))},
            ],
        )

        aiquestion = airesponse.choices[0].message.content
        out_message = self.settings.get_string(
            guild_id, "techthurs_out_message", message=aiquestion, taco_count=amount, taco_word=taco_word
        )

        if not aiquestion:
            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", "No tech thursday topic/question generated"
            )
            return

        allow_publish = ai_settings.get("allow_publish", False)
        if allow_publish:
            message = await self.messaging.send_embed(
                channel=out_channel,
                title=self.settings.get_string(guild_id, "techthurs_out_title"),
                message=out_message,
                content=message_content,
                color=0x00FF00,
            )
            self.techthurs_db.save_techthurs(
                guildId=guild_id,
                message=aiquestion,
                image=None,
                author=user.id,
                channel_id=message.channel.id,
                message_id=message.id,
            )
            if isinstance(ctx, discord.Interaction):
                # respond to the interaction
                await ctx.response.send_message(content="Question generated", ephemeral=True)
        else:
            # get the interaction from the context
            interaction = None
            if isinstance(ctx, discord.Interaction):
                interaction = ctx

            if interaction:
                await interaction.response.send_message(content=out_message, ephemeral=True)
            else:
                # send the message in a DM to the user
                await user.send(out_message)

    def get_cog_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section="tacos")


async def setup(bot):
    await bot.add_cog(TechThursdays(bot))
