import async_timeout
import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import collections

from discord.ext.commands.cooldowns import BucketType
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure

from . import utils
from . import logger
from . import loglevel
from . import settings
from . import mongo
from . import dbprovider
from . import tacotypes

import inspect

class DiscordHelper():
    def __init__(self, bot):
        self.settings = settings.Settings()
        self.bot = bot
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

    def create_context(self, bot = None, author = None, guild = None, channel = None, message = None, invoked_subcommand = None, **kwargs):
        ctx_dict = {"bot": bot, "author": author, "guild": guild, "channel": channel, "message": message, "invoked_subcommand": invoked_subcommand}
        ctx = collections.namedtuple("Context", ctx_dict.keys())(*ctx_dict.values())
        return ctx

    async def move_message(self, message, targetChannel, author: discord.User = None, who: discord.User = None, reason: str = None, fields = None, remove_fields = None, color: int = None):
        if not message:
            return
        if not targetChannel:
            return
        if not author:
            author = message.author

        if not message.guild:
            return
        guild_id = message.guild.id

        try:
            if len(message.embeds) == 0:
                description = f"{message.content}"
                title = ""
                embed_fields = []
            else:
                embed = message.embeds[0]
                title = embed.title
                if embed.description is None or embed.description == discord.Embed.Empty:
                    description = ""
                else:
                    description = f"{embed.description}"
                # lib3ration 500 bits: oh look a Darth Fajitas
                embed_fields = embed.fields
                if color is None and embed.color is not None:
                    color = embed.color

            if who:
                footer = f"{self.settings.get_string(guild_id, 'moved_by', user=f'{who.name}#{who.discriminator}')} - {reason or self.settings.get_string(guild_id, 'no_reason')}"

            if color is None:
                color = 0x7289da

            target_embed = discord.Embed(title=title, description=description, color=color)
            target_embed.set_author(name=author.name, icon_url=author.avatar_url)
            if footer:
                target_embed.set_footer(text=footer)
            else:
                target_embed.set_footer(text=self.settings.get_string(guild_id, 'developed_by', user=self.settings.author))
            if remove_fields is None:
                remove_fields = []

            if embed_fields is not None:
                for f in [ ef for ef in embed_fields if ef.name not in [ rfi['name'] for rfi in remove_fields ]]:
                    target_embed.add_field(name=f.name, value=f.value, inline=f.inline)
            if fields is not None:
                for f in [ rf for rf in fields if rf['name'] not in [ rfi['name'] for rfi in remove_fields ] ]:
                    target_embed.add_field(name=f['name'], value=f['value'], inline=f['inline'] if 'inline' in f else False)

            files = [await a.to_file() for a in message.attachments]

            if len(files) > 0 or target_embed != discord.Embed.Empty:
                await targetChannel.send(files=files, embed=target_embed)
        except Exception as ex:
            self.log.error(0, "discordhelper.move_message", str(ex), traceback.format_exc())

    async def sendEmbed(self, channel, title, message, fields=None, delete_after=None, footer=None, components=None, color=0x7289da, author=None):
        if color is None:
            color = 0x7289da
        guild_id = 0
        if channel.guild:
            guild_id = channel.guild.id
        embed = discord.Embed(title=title, description=message, color=color)
        if author:
            embed.set_author(name=f"{author.name}#{author.discriminator}", icon_url=author.avatar_url)
        if embed.fields is not None:
            for f in embed.fields:
                embed.add_field(name=f['name'], value=f['value'], inline=f['inline'] if 'inline' in f else False)
        if fields is not None:
            for f in fields:
                embed.add_field(name=f['name'], value=f['value'], inline=f['inline'] if 'inline' in f else False)
        if footer is None:
            embed.set_footer(text=self.settings.get_string(guild_id, 'developed_by', user=self.settings.author))
        else:
            embed.set_footer(text=footer)
        return await channel.send(embed=embed, delete_after=delete_after, components=components)

    async def updateEmbed(self, message, title = None, description = None, description_append: bool = True, fields = None, footer = None, components = None, color = 0x7289da, author = None):
        if not message or len(message.embeds) == 0:
            return
        if color is None:
            color = 0x7289da
        guild_id = 0
        if message.guild:
            guild_id = message.guild.id
        embed = message.embeds[0]
        if title is None:
            title = embed.title
        if description is not None:
            if description_append:
                edescription = ""
                if embed.description is not None and embed.description != discord.Embed.Empty:
                    edescription = embed.description

                description = edescription + "\n\n" + description
            else:
                description = description
        else:
            if embed.description is not None and embed.description != discord.Embed.Empty:
                description = embed.description
            else:
                description = ""
        updated_embed = discord.Embed(color=color, title=embed.title, description=f"{description}", footer=embed.footer)
        for f in embed.fields:
            updated_embed.add_field(name=f.name, value=f.value, inline=f.inline)
        if fields is not None:
            for f in fields:
                updated_embed.add_field(name=f['name'], value=f['value'], inline=f['inline'] if 'inline' in f else False)
        if footer is None:
            updated_embed.set_footer(text=self.settings.get_string(guild_id, 'developed_by', user=self.settings.author))
        else:
            updated_embed.set_footer(text=footer)

        if author:
            updated_embed.set_author(name=f"{author.name}#{author.discriminator}", icon_url=author.avatar_url)

        await message.edit(embed=updated_embed)

    async def notify_of_error(self, ctx):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
        await self.sendEmbed(ctx.channel, self.settings.get_string(guild_id, 'error'), self.settings.get_string(guild_id, 'error_ocurred', user=ctx.author.mention), delete_after=30)

    async def notify_bot_not_initialized(self, ctx, subcommand: str = None):
        channel = ctx.channel
        if not channel:
            channel = ctx.author
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id

        if not ctx.author.guild_permissions.administrator:
            await self.sendEmbed(ctx.channel, self.settings.get_string(guild_id, 'error'),
                self.settings.get_string(guild_id, 'not_initialized_user', user=ctx.author.mention), delete_after=30)
        else:
            # get the bot's prefix
            prefix = await self.bot.get_prefix(ctx.message)[0]
            await self.sendEmbed(ctx.channel, self.settings.get_string(guild_id, 'error'),
                self.settings.get_string(guild_id, 'not_initialized_admin',
                    user=ctx.author.mention, prefix=prefix,
                    subcommand=subcommand),
                delete_after=30)

    async def taco_give_user(self, guildId: int, fromUser: typing.Union[discord.User, discord.Member], toUser: typing.Union[discord.User, discord.Member], reason: str = None, give_type: tacotypes.TacoTypes = tacotypes.TacoTypes.CUSTOM, taco_amount: int = 1):
        try:
            _method = inspect.stack()[0][3]
            # get taco settings
            taco_settings = self.settings.get_settings(self.db, guildId, "tacos")
            if not taco_settings:
                # raise exception if there are no tacos settings
                self.log.error(guildId, "tacos.on_message", f"No tacos settings found for guild {guildId}")
                return
            taco_count = taco_amount

            if give_type != tacotypes.TacoTypes.CUSTOM:
                taco_count = taco_settings[tacotypes.TacoTypes.get_string_from_taco_type(give_type)]
            elif give_type == tacotypes.TacoTypes.CUSTOM:
                taco_count = taco_amount
            else:
                self.log.warn(guildId, "tacos.on_message", f"Invalid taco type {give_type}")
                return

            # only reject <= 0 tacos if it is not custom type
            if taco_count <= 0 and give_type != tacotypes.TacoTypes.CUSTOM:
                self.log.warn(guildId, "tacos.on_message", f"Invalid taco count {taco_count}")
                return

            reason_msg = reason if reason else self.settings.get_string(guildId, 'no_reason')

            total_taco_count = self.db.add_tacos(guildId, toUser.id, taco_count)
            await self.tacos_log(guildId, toUser, fromUser, taco_count, total_taco_count, reason_msg)
            return total_taco_count
        except Exception as e:
            self.log.error(guildId, _method, str(e), traceback.format_exc())

    async def taco_purge_log(self, guild_id: int, toMember: typing.Union[discord.User, discord.Member], fromMember: typing.Union[discord.User, discord.Member], reason: str):
        _method = inspect.stack()[0][3]
        try:

            taco_settings = self.settings.get_settings(self.db, guild_id, "tacos")
            if not taco_settings:
                # raise exception if there are no tacos settings
                raise Exception("No tacos settings found")

            taco_log_channel_id = taco_settings["taco_log_channel_id"]
            log_channel = await self.get_or_fetch_channel(int(taco_log_channel_id))

            self.log.debug(guild_id, _method, f"{fromMember.name} purged all tacos from {toMember.name} for {reason}")
            if log_channel:
                await log_channel.send(self.settings.get_string(guild_id, "tacos_purged_log", touser=toMember.name, fromuser=fromMember.name, reason=reason))
        except Exception as e:
            self.log.error(guild_id, _method, str(e), traceback.format_exc())


    async def tacos_log(self, guild_id: int, toMember: discord.Member, fromMember: discord.Member, count: int, total_tacos: int, reason: str):
        _method = inspect.stack()[0][3]
        try:

            taco_settings = self.settings.get_settings(self.db, guild_id, "tacos")
            if not taco_settings:
                # raise exception if there are no tacos settings
                raise Exception("No tacos settings found")

            taco_log_channel_id = taco_settings["taco_log_channel_id"]
            log_channel = await self.get_or_fetch_channel(int(taco_log_channel_id))
            taco_word = self.settings.get_string(guild_id, "taco_plural")
            if count == 1:
                taco_word = self.settings.get_string(guild_id, "taco_singular")

            action = self.settings.get_string(guild_id, "tacos_log_action_received")
            if count < 0:
                action  = self.settings.get_string(guild_id, "tacos_log_action_lost")

            positive_count = abs(count)

            self.log.debug(guild_id, _method, f"{toMember.name}#{toMember.discriminator} {action} {positive_count} {taco_word} from {fromMember.name}#{fromMember.discriminator} for {reason}")
            if log_channel:
                await log_channel.send(self.settings.get_string(guild_id, "tacos_log_message",
                    touser=toMember.name, action=action,
                    positive_count=positive_count, taco_word=taco_word,
                    fromuser=fromMember.name, reason=reason,
                    total_tacos=total_tacos))
        except Exception as e:
            self.log.error(guild_id, _method, str(e), traceback.format_exc())

    async def get_or_fetch_user(self, userId: int):
        _method = inspect.stack()[1][3]
        try:
            if userId:
                user = self.bot.get_user(userId)
                if not user:
                    user = await self.bot.fetch_user(userId)
                return user
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_member(self, guildId: int, userId: int):
        _method = inspect.stack()[1][3]
        try:
            if not guildId:
                return None
            guild = self.bot.get_guild(guildId)
            if not guild:
                guild = await self.bot.fetch_guild(guildId)
            if not guild:
                return None

            if userId:
                user = guild.get_member(userId)
                if not user:
                    user = await guild.fetch_member(userId)
                return user
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_channel(self, channelId: int):
        _method = inspect.stack()[1][3]
        try:
            if channelId:
                chan = self.bot.get_channel(channelId)
                if not chan:
                    chan = await self.bot.fetch_channel(channelId)
                return chan
            else:
                return  None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    def get_by_name_or_id(self, iterable, nameOrId: typing.Union[int, str]):
        if isinstance(nameOrId, str):
            return discord.utils.get(iterable, name=str(nameOrId))
        elif isinstance(nameOrId, int):
            return discord.utils.get(iterable, id=int(nameOrId))
        else:
            return None

    async def ask_yes_no(self, ctx, targetChannel, question: str, title: str = "TacoBot", timeout: int = 60):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        channel = targetChannel if targetChannel else ctx.channel if ctx.channel else ctx.author
        buttons = [
            create_button(style=ButtonStyle.green, label=self.settings.get_string(ctx.guild.id, "yes"), custom_id="YES"),
            create_button(style=ButtonStyle.red, label=self.settings.get_string(ctx.guild.id, "no"), custom_id="NO")
        ]
        yes_no = False
        action_row = create_actionrow(*buttons)
        timeout = timeout if timeout else 60
        yes_no_req = await self.sendEmbed(channel, title, question, components=[action_row], delete_after=timeout, footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout))
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=timeout)
        except asyncio.TimeoutError:
            await self.sendEmbed(channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5)
        else:
            yes_no = utils.str2bool(button_ctx.custom_id)
            await yes_no_req.delete()
        return yes_no

    async def wait_for_user_invoke_cleanup(self, ctx):
        try:
            guild_id = ctx.guild.id
            channel = ctx.channel

            waiting_invokes = self.db.get_wait_invokes(guildId=guild_id, channelId=channel.id)
            if waiting_invokes:
                for w in waiting_invokes:
                    wi_message_id = int(w['message_id'])
                    if wi_message_id:
                        self.log.debug(guild_id, "suggestions.on_ready", f"Found waiting invoke {w['message_id']}")
                        try:
                            wi_message = await channel.fetch_message(wi_message_id)
                            if wi_message:
                                await wi_message.delete()
                                self.log.debug(guild_id, "suggestions.on_ready", f"Deleted waiting invoke {w['message_id']}")
                        except discord.errors.NotFound as nf:
                            self.log.warn(guild_id, "suggestions.on_ready", str(nf))

                        self.db.untrack_wait_invoke(guildId=guild_id, channelId=channel.id, messageId=wi_message_id)
        except Exception as e:
            self.log.error(guild_id, "suggestions.on_ready", str(e), traceback.format_exc())

    async def wait_for_user_invoke(self, ctx, targetChannel, title: str, description: str, button_label: str = "Yes", button_id: str = "YES"):
        def check(m):
            return True
        channel = targetChannel if targetChannel else ctx.channel if ctx.channel else ctx.author

        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0
        buttons = [
            create_button(style=ButtonStyle.green, label=button_label or self.settings.get_string(ctx.guild.id, "yes"), custom_id=button_id or "YES"),
        ]
        action_row = create_actionrow(*buttons)
        invoke_req = await self.sendEmbed(channel, title, description, components=[action_row])
        self.db.track_wait_invoke(guild_id, channel.id, invoke_req.id)
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check, components=action_row)
        except asyncio.TimeoutError:
            # this should never happen because there is no timeout
            await self.sendEmbed(channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5)
        else:
            await invoke_req.delete()
            self.db.untrack_wait_invoke(guild_id, channel.id, invoke_req.id)
        return button_ctx

    async def ask_channel_by_name_or_id(self, ctx, title: str = "TacoBot", description: str = "Enter the name of the channel", timeout: int = 60):
        _method = inspect.stack()[1][3]
        try:
            guild = ctx.guild
            if not guild:
                return None
            def check_channel(m):
                c = self.get_by_name_or_id(guild.channels, m.content)
                if c:
                    return True
                else:
                    return False
            target_channel = ctx.channel if ctx.channel else ctx.author

            channel_ask = await self.sendEmbed(target_channel, title, f'{description}', delete_after=timeout, footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout))
            try:
                channelResp = await self.bot.wait_for('message', check=check_channel, timeout=timeout)
            except asyncio.TimeoutError:
                await self.sendEmbed(target_channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5)
                return None
            else:
                selected_channel = self.get_by_name_or_id(guild.channels, channelResp.content)
                await channelResp.delete()
                await channel_ask.delete()
                return selected_channel
        except Exception as ex:
            self.log.error(ctx.guild.id, _method, str(ex), traceback.format_exc())
            return None

    async def ask_channel(self, ctx, title: str = "Choose Channel", message: str = "Please choose a channel.", allow_none: bool = False, timeout: int = 60):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        options = []
        channels = [c for c in ctx.guild.channels if c.type == discord.ChannelType.text]
        channels.sort(key=lambda c: c.position)
        sub_message = ""
        max_items = 24 if not allow_none else 23
        if len(channels) >= max_items:
            self.log.warn(ctx.guild.id, _method, f"Guild has more than 24 channels. Total Channels: {str(len(channels))}")
            options.append(create_select_option(label=self.settings.get_string(ctx.guild.id, "other"), value="0", emoji="⏭"))
            # sub_message = self.get_string(guild_id, 'ask_admin_role_submessage')
        if allow_none:
            options.append(create_select_option(label=self.settings.get_string(ctx.guild.id, "none"), value="-1", emoji="⛔"))

        for c in channels[:max_items]:
            options.append(create_select_option(label=c.name, value=str(c.id), emoji="🏷"))

        select = create_select(
            options=options,
            placeholder="Channel",
            min_values=1, # the minimum number of options a user must select
            max_values=1 # the maximum number of options a user can select
        )

        action_row = create_actionrow(select)
        ask_context = await self.sendEmbed(ctx.channel, title, message, delete_after=timeout, footer=f"You have {timeout} seconds to respond.", components=[action_row])
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=60.0)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5)
        else:
            chan_id = int(button_ctx.selected_options[0])
            await ask_context.delete()
            if chan_id == 0:
                asked_channel = await self.ask_channel_by_name_or_id(ctx, title, self.settings.get_string(guild_id, "ask_name_of_channel"), timeout=timeout)
                chan_id = asked_channel.id if asked_channel else None

            if chan_id is None:
                # manual entered channel not found
                await self.sendEmbed(ctx.channel, title, self.settings.get_string(guild_id, "unknown_channel", user=ctx.author.mention, channel_id=chan_id), delete_after=5)
                return None

            if chan_id == -1:
                # user selected none
                return None

            selected_channel = discord.utils.get(ctx.guild.channels, id=chan_id)
            if selected_channel:
                self.log.debug(guild_id, _method, f"{ctx.author.mention} selected the channel '{selected_channel.name}'")
                await self.sendEmbed(ctx.channel, title, self.settings.get_string(guild_id, "selected_channel_message", user=ctx.author.mention, channel=selected_channel.name), delete_after=5)
                return selected_channel
            else:
                await self.sendEmbed(ctx.channel, title, self.settings.get_string(guild_id, "unknown_channel", user=ctx.author.mention, channel_id=chan_id), delete_after=5)
                return None


    async def ask_number(self, ctx, title: str = "Enter Number", message: str = "Please enter a number.", min_value: int = 0, max_value: int = 100, timeout: int = 60):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        def check_range(m):
            if check_user(m):
                if m.content.isnumeric():
                    val = int(m.content)
                    return (val >= min_value and val <= max_value)
                return False

        number_ask = await self.sendEmbed(ctx.channel, title, f'{message}', delete_after=timeout, footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout))
        try:
            numberResp = await self.bot.wait_for('message', check=check_range, timeout=timeout)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5)
            return None
        else:
            numberValue = int(numberResp.content)
            await numberResp.delete()
            await number_ask.delete()
        return numberValue

    async def ask_text(self, ctx, targetChannel, title: str = "Enter Text Response", message: str = "Please enter your response.", timeout: int = 60, color=None):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        channel = targetChannel if targetChannel else ctx.channel if ctx.channel else ctx.author
        delete_user_message = True
        if not ctx.guild:
            channel = ctx.author
            delete_user_message = False

        text_ask = await self.sendEmbed(channel, title, f'{message}', delete_after=timeout, footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout), color=color)
        try:
            textResp = await self.bot.wait_for('message', check=check_user, timeout=timeout)
        except asyncio.TimeoutError:
            await self.sendEmbed(channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5)
            return None
        else:
            if delete_user_message:
                try:
                    await textResp.delete()
                except:
                    pass
            await text_ask.delete()
        return textResp.content

    async def ask_role_list(self, ctx, title: str = "Choose Role", message: str = "Please choose a role.", allow_none: bool = False, min_select: int = 1, max_select: int = 1, exclude_roles: list = None, timeout: int = 60):
        def check_user(m):
            same = m.author.id == ctx.author.id
            return same
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        options = []
        roles = [r for r in ctx.guild.roles if exclude_roles is None or r.id not in [x.id for x in exclude_roles]]
        print(f"{len(roles)} roles")
        roles.sort(key=lambda r: r.position)
        sub_message = ""
        if len(roles) == 0:
            self.log.warn(ctx.guild.id, _method, f"Forcing 'other' option for role list as there are no roles to select.")
            options.append(create_select_option(label=self.settings.get_string(ctx.guild.id, "other"), value="0", emoji="⏭"))
        if len(roles) >= 24:
            self.log.warn(ctx.guild.id, _method, f"Guild has more than 24 roles. Total roles: {str(len(roles))}")
            options.append(create_select_option(label=self.settings.get_string(ctx.guild.id, "other"), value="0", emoji="⏭"))
            # sub_message = self.get_string(guild_id, 'ask_admin_role_submessage')
        if allow_none:
            options.append(create_select_option(label=self.settings.get_string(ctx.guild.id, "none"), value="-1", emoji="⛔"))

        for r in roles[:24]:
            options.append(create_select_option(label=r.name, value=str(r.id), emoji="🏷"))

        select = create_select(
            options=options,
            placeholder=title,
            min_values=1, # the minimum number of options a user must select
            max_values=1 # the maximum number of options a user can select
        )

        action_row = create_actionrow(select)
        ask_context = await self.sendEmbed(ctx.channel, title, message, delete_after=timeout, footer=self.settings.get_string(ctx.guild.id, "footer_XX_seconds", seconds=timeout), components=[action_row])
        try:
            button_ctx: ComponentContext = await wait_for_component(self.bot, check=check_user, components=action_row, timeout=timeout)
        except asyncio.TimeoutError:
            await self.sendEmbed(ctx.channel, title, self.settings.get_string(ctx.guild.id, "took_too_long"), delete_after=5)
        else:
            role_id = int(button_ctx.selected_options[0])
            if role_id == 0:
                await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, ENTER ROLE NAME", delete_after=5)
                return
                # chan_id = await self.ask_channel_by_name_or_id(ctx, title)

            await ask_context.delete()
            selected_role= discord.utils.get(ctx.guild.roles, id=role_id)
            if selected_role:
                self.log.debug(guild_id, _method, f"{ctx.author.mention} selected the role '{selected_role.name}'")
                await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, You have selected channel '{selected_role.name}'", delete_after=5)
                return selected_role
            else:
                await self.sendEmbed(ctx.channel, title, f"{ctx.author.mention}, Unknown Role.", delete_after=5)
                return None

    async def is_admin(self, guildId: int, userId: int):
        member = await self.get_or_fetch_member(guildId, userId)
        if not member:
            return False
        # does the user have admin permissions?
        return member.guild_permissions.administrator
