import discord
from discord.ext import commands
import asyncio
import json
import traceback
import datetime
import sys
import os
import glob
import typing

from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands import has_permissions, CheckFailure, Context

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider
from .lib import tacotypes

import inspect


class TacoTuesday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "tacotuesday"
        self.SELF_DESTRUCT_TIMEOUT = 30
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "taco_tuesday.__init__", "Initialized")

    @commands.group()
    async def tuesday(self, ctx):
        pass

    @tuesday.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def new(self, ctx, member: discord.Member, tweet: str):
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

            cog_settings = self.get_cog_settings(guild_id)
            tacos_settings = self.get_tacos_settings(guild_id)

            message_template = cog_settings.get("message_template", None)
            if not message_template:
                self.log.debug(guild_id, "taco_tuesday.new", f"Message template not set")
                return

            tag_role_id = cog_settings.get("tag_role", None)
            tag_role_mention = ""
            if tag_role_id:
                tag_role_mention = f"<@&{tag_role_id}>"

            output_channel_id = cog_settings.get("output_channel_id", None)
            if not output_channel_id:
                self.log.debug(guild_id, "taco_tuesday.new", f"Output channel not set")
                return

            output_channel = await self.discord_helper.get_or_fetch_channel(int(output_channel_id))
            if not output_channel:
                self.log.debug(guild_id, "taco_tuesday.new", f"Output channel not found")
                return

            message = utils.str_replace(
                message_template,
                tweet=tweet,
                role=tag_role_mention,
                tacos=tacos_settings.get(tacotypes.TacoTypes.get_string_from_taco_type(tacotypes.TacoTypes.TACO_TUESDAY), 250),
            )


            result_message = await output_channel.send(content=message)
            # add import_emoji to message so we can archive it later
            import_emoji = cog_settings.get("import_emoji", ["🇮"])
            if len(import_emoji) > 0:
                await result_message.add_reaction(import_emoji[0])

            self._import_taco_tuesday(result_message)

            await self._set_taco_tuesday_user(ctx=ctx, member=member)

        except Exception as e:
            self.log.error(guild_id, "taco_tuesday.new", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)


    @tuesday.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set(self, ctx, member: discord.Member):
        """Sets the user associated with the taco tuesday"""
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

            await self._set_taco_tuesday_user(ctx=ctx, member=member)

        except Exception as e:
            self.log.error(ctx.guild.id, "taco_tuesday.set", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)
    @tuesday.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def give(self, ctx, member: discord.Member):
        try:
            await ctx.message.delete()

            await self.give_user_tacotuesday_tacos(ctx.guild.id, member.id, ctx.channel.id)

        except Exception as e:
            self.log.error(ctx.guild.id, "taco_tuesday.give", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    async def _on_raw_reaction_add_import(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id

        # check if the user that reacted is in the admin role
        if not await self.discord_helper.is_admin(guild_id, payload.user_id):
            self.log.debug(guild_id, _method, f"User {payload.user_id} is not an admin")
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        if reaction.count > 1:
            self.log.debug(
                guild_id,
                _method,
                f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}",
            )
            return

        self._import_taco_tuesday(message)

    async def _on_raw_reaction_add_archive(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id

        # check if the user that reacted is in the admin role
        if not await self.discord_helper.is_admin(guild_id, payload.user_id):
            self.log.debug(guild_id, _method, f"User {payload.user_id} is not an admin")
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        cog_settings = self.get_cog_settings(guild_id)

        # check if message has the import emoji
        was_imported = False
        for m in message.reactions:
            if str(m.emoji) in cog_settings.get("import_emoji", ["🇮"]):
                was_imported = True
                break
        if not was_imported:
            self.log.debug(guild_id, _method, f"Message {payload.message_id} was not imported. No need to archive.")
            return

        reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        if reaction.count > 1:
            self.log.debug(
                guild_id,
                _method,
                f"Reaction {payload.emoji.name} has already been added to message {payload.message_id}",
            )
            return

        await self._archive_taco_tuesday(message, cog_settings)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        try:
            if payload.event_type != "REACTION_ADD":
                return

            ###
            # archive_enabled: true,
            # archive_emoji: [
            #     '🔒'
            # ],
            # archive_channel_id: '948689068961706034',
            ###

            cog_settings = self.get_cog_settings(guild_id)

            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, _method, f"Taco Tuesday not enabled")
                return

            # check if reaction is to archive the message
            reaction_archive_emojis = cog_settings.get("archive_emoji", ["🔒"])
            reaction_import_emojis = cog_settings.get("import_emoji", ["🇮"])
            check_list = reaction_archive_emojis + reaction_import_emojis
            if str(payload.emoji.name) not in check_list:
                self.log.debug(guild_id, _method, f"Reaction {payload.emoji.name} not in check list")
                return

            if str(payload.emoji.name) in reaction_archive_emojis:
                if cog_settings.get("archive_enabled", False):
                    self.log.debug(guild_id, _method, f"Archive is enabled. Archiving message")
                    await self._on_raw_reaction_add_archive(payload)
                    return

            today = datetime.datetime.now()
            if today.weekday() != 1:  # 1 = Tuesday
                return

            if str(payload.emoji.name) in reaction_import_emojis:
                await self._on_raw_reaction_add_import(payload)
                return

        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            # await self.discord_helper.notify_of_error(ctx)

    async def _archive_taco_tuesday(self, message: discord.Message, cog_settings: dict = None):
        _method = inspect.stack()[0][3]
        guild_id = message.guild.id
        try:
            archive_channel_id = cog_settings.get("archive_channel_id", None)
            if not archive_channel_id:
                self.log.error(
                    guild_id, "tacotuesday._archive_taco_tuesday", f"No archive_channel_id found for guild {guild_id}"
                )
                return

            archive_channel = await self.discord_helper.get_or_fetch_channel(int(archive_channel_id))
            if not archive_channel:
                self.log.error(
                    guild_id,
                    "tacotuesday._archive_taco_tuesday",
                    f"Could not find archive channel {archive_channel_id} for guild {guild_id}",
                )
                return

            # get taco tuesday info
            taco_tuesday_info = self.db.taco_tuesday_get_by_message(guildId=guild_id, channelId=message.channel.id, messageId=message.id)
            if taco_tuesday_info:
                # get the user id
                user_id = taco_tuesday_info.get("user_id", None)
                if user_id:
                    # get the member
                    user = await self.discord_helper.get_or_fetch_member(guildId=guild_id, userId=int(user_id))
                    if user:
                        cog_settings = self.get_cog_settings(guild_id)
                        focus_role_id = cog_settings.get("focus_role", None)
                        if focus_role_id:
                            remove_role_list = [focus_role_id]
                            # remove the user from the taco tuesday role
                            await self.discord_helper.add_remove_roles(
                                user=user,
                                check_list=[],
                                remove_list=remove_role_list,
                                add_list=[],
                                allow_everyone=True
                            )

            # build field info:
            fields = [
                { "name": "Reactions", "value": f"-----", "inline": False }
            ]
            for r in message.reactions:
                if str(r.emoji) in cog_settings.get("import_emoji", ["🇮"]):
                    continue
                if str(r.emoji) in cog_settings.get("archive_emoji", ["🔒"]):
                    continue
                fields.append(
                    {
                        "name": str(r.emoji),
                        "value": f"{r.count}",
                        "inline": True,
                    }
                )


            moved_message = await self.discord_helper.move_message(
                message=message,
                targetChannel=archive_channel,
                who=self.bot.user,
                fields=fields,
                reason="TACO Tuesday archive"
            )

            # Should Update the entry to the new channel and message id
            self.db.taco_tuesday_update_message(
                guildId=guild_id,
                channelId=message.channel.id,
                messageId=message.id,
                newChannelId=moved_message.channel.id,
                newMessageId=moved_message.id
            )

            await message.delete()

            await self.discord_helper.sendEmbed(
                message.channel,
                title="TACO Tuesday",
                message=f"Message archived to {archive_channel.mention}",
                color=discord.Color.green().value,
                delete_after=10,
            )

        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            # await self.discord_helper.notify_of_error(ctx)

    async def _set_taco_tuesday_user(self, ctx: commands.Context, member: discord.Member):
        if ctx.guild is None:
            raise Exception("This command can only be used in a guild")

        guild_id = ctx.guild.id
        cog_settings = self.get_cog_settings(guild_id)
        self.db.taco_tuesday_set_user(guild_id, member.id)

        # get focus role id
        focus_role_id = cog_settings.get("focus_role", None)
        if not focus_role_id:
            self.log.debug(guild_id, "taco_tuesday.set", f"Focus role not set")
            return

        self.log.debug(guild_id, "taco_tuesday.set", f"Adding user {member.id} to focus role {focus_role_id}")
        # add user to focus_role
        await self.discord_helper.add_remove_roles(
            user=member,
            check_list=[],
            add_list=[focus_role_id],
            remove_list=[],
            allow_everyone=True
        )
    def _import_taco_tuesday(self, message: discord.Message):
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
            "taco_tuesday._import_taco_tuesday",
            f"Importing TACO Tuesday message {message_id} from channel {channel_id} in guild {guild_id} for user {message_author.id} with text {text} and image {image_url}",
        )
        self.db.save_taco_tuesday(
            guildId=guild_id,
            message=text or "",
            image=image_url or "",
            author=message_author.id,
            channel_id=channel_id,
            message_id=message_id,
        )

    async def give_user_tacotuesday_tacos(self, guild_id, user_id, channel_id):
        ctx = None
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
                    guild_id, "tacotuesday.give_user_tacotuesday_tacos", f"No output channel found for guild {guild_id}"
                )
                return
            message = None

            # get bot
            bot = self.bot
            ctx = self.discord_helper.create_context(
                bot=bot, guild=guild, author=member, channel=channel, message=message
            )

            # track that the user answered the question.
            self.db.track_taco_tuesday(guild_id, member.id)

            tacos_settings = self.get_tacos_settings(guild_id)
            if not tacos_settings:
                self.log.warn(
                    guild_id, "tacotuesday.give_user_tacotuesday_tacos", f"No tacos settings found for guild {guild_id}"
                )
                return

            amount = tacos_settings.get("taco_tuesday_count", 250)

            tacos_word = self.settings.get_string(guild_id, "taco_singular")
            if amount > 1:
                tacos_word = self.settings.get_string(guild_id, "taco_plural")

            reason_msg = self.settings.get_string(guild_id, "taco_tuesday_reason")

            await self.discord_helper.sendEmbed(
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
                guild_id, self.bot.user, member, reason_msg, tacotypes.TacoTypes.TACO_TUESDAY, taco_amount=amount
            )

        except Exception as e:
            self.log.error(guild_id, "tacotuesday.give_user_tacotuesday_tacos", str(e), traceback.format_exc())
            if ctx:
                await self.discord_helper.notify_of_error(ctx)

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
    await bot.add_cog(TacoTuesday(bot))
