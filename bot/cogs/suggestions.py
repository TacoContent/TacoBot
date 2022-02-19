import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import math
import inspect
import uuid
import datetime

from discord.ext.commands.cooldowns import BucketType
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import models
from .lib import settings
from .lib import mongo
from .lib import dbprovider

class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)

        self.SETTINGS_SECTION = "suggestions"

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "suggestions.__init__", "Initialized")

    @commands.group(aliases=["suggestion"])
    async def suggest(self, ctx):
        try:
            guild_id = 0
            if ctx.guild is not None:
                guild_id = ctx.guild.id
                await ctx.message.delete()
            else:
                # only allow suggestions in guilds
                self.log.debug(0, "suggestions.suggest", f"Command {ctx.command.name} not allowed in DM")
                return
            if ctx.author.bot:
                return # ignore bots

            if ctx.invoked_subcommand is None:

                ss = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
                if not ss:
                    # raise exception if there are no suggestion settings
                    self.log.debug(guild_id, "suggestions.on_message", f"No suggestion settings found for guild {guild_id}")
                    raise Exception("No suggestion settings found")

                # create suggestion
                channel_settings = [ c for c in ss['channels'] if c['id'] == str(ctx.channel.id) ]
                if not channel_settings:
                    self.log.debug(guild_id, "suggestions.on_message", f"No suggestion settings found for channel {ctx.channel.id}")
                    # notify user that the channel they are in is not configured for suggestions
                    await self.discord_helper.sendEmbed(ctx.channel, "Suggestions", "This channel is not configured for suggestions. Please run the `.taco suggest` in a channel that is configured for suggestions.", delete_after=20, color=0xFF0000)
                    return
                else:
                    channel_settings = channel_settings[0]
                response_channel = await self.discord_helper.get_or_fetch_channel(int(channel_settings['id']))
                if not response_channel:
                    self.log.debug(guild_id, "suggestions.on_message", f"No channel found for channel id {channel_settings['id']}")
                    return

                # dm user with a message and ask for their suggestion
                create_now = await self.discord_helper.ask_yes_no(ctx, ctx.author, "Are you ready to enter your suggestion?", "Create Suggestion", timeout=60)
                if create_now:
                    suggestion_title = await self.discord_helper.ask_text(ctx, ctx.author, "Create Suggestion", "What is the title of your suggestion?", timeout=60)
                    if suggestion_title is None:
                        suggestion_title = "Suggestion"
                    suggestion_message = await self.discord_helper.ask_text(ctx, ctx.author, "Create Suggestion", "Please enter your suggestion below.\n\n**Note:**\nYou can respond with `cancel` to cancel your suggestion request.", color=0x00ff00, timeout=None)
                    if suggestion_message is None or suggestion_message.lower().strip() == "cancel":
                        await self.discord_helper.sendEmbed(ctx.author, "Suggestion Cancelled", "Your suggestion request has been cancelled.", color=0x00ff00)
                        return

                    legend = [
                        { "name": "Voting", "value": f"{channel_settings['vote_up_emoji']} Up Vote\n{channel_settings['vote_neutral_emoji']} Neutral Vote\n{channel_settings['vote_down_emoji']} Down Vote", "inline": True },
                        { "name": "🛡 Actions", "value": f"{channel_settings['admin_approve_emoji']} Approve\n{channel_settings['admin_consider_emoji']} Consider\n{channel_settings['admin_implemented_emoji']} Implemented\n{channel_settings['admin_reject_emoji']} Reject\n{channel_settings['admin_close_emoji']} Close\n{channel_settings['admin_delete_emoji']} Delete", "inline": True },
                    ]

                    s_message = await self.discord_helper.sendEmbed(response_channel, f"{suggestion_title}", message=f"{suggestion_message}", author=ctx.author, fields=legend)

                    vote_emoji = [
                        channel_settings["vote_up_emoji"],
                        channel_settings["vote_neutral_emoji"],
                        channel_settings["vote_down_emoji"]
                 ]
                    admin_emoji = [
                        channel_settings["admin_approve_emoji"],
                        channel_settings["admin_consider_emoji"],
                        channel_settings["admin_implemented_emoji"],
                        channel_settings["admin_reject_emoji"],
                        channel_settings["admin_close_emoji"],
                        channel_settings["admin_delete_emoji"]
                        ]
                    reactions = vote_emoji
                    for r in reactions:
                        # add reaction to the message from the bot
                        await s_message.add_reaction(r)

                    suggestion_data = {
                        "id": uuid.uuid4().hex,
                        "message_id": s_message.id,
                        "author_id": ctx.author.id,
                        "suggestion" : {
                            "title": suggestion_title,
                            "description": suggestion_message
                        }
                    }
                    self.db.add_suggestion(guild_id, s_message.id, suggestion_data)
                pass
            else:
                pass
        except Exception as e:
            self.log.error(guild_id, "suggestions.suggest", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        try:
            guild_id = payload.guild_id
            # ignore if not in a guild
            if guild_id is None or guild_id == 0:
                return
            if payload.event_type != 'REACTION_ADD':
                return
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if user.bot:
                return

            # get suggestion from database
            suggestion = self.db.get_suggestion(guild_id, payload.message_id)
            if not suggestion or suggestion['message_id'] != str(payload.message_id):
                self.log.debug(guild_id, "suggestions.on_raw_reaction_add", f"No suggestion found for message id {payload.message_id}")
                return

            author = await self.discord_helper.get_or_fetch_user(int(suggestion['author_id']))
            print(f"author: {author}")

            ss = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not ss:
                # raise exception if there are no suggestion settings
                self.log.debug(guild_id, "suggestions.on_message", f"No suggestion settings found for guild {guild_id}")
                raise Exception("No suggestion settings found")

            channel_settings = [ c for c in ss['channels'] if c['id'] == str(channel.id) ]
            if not channel_settings:
                self.log.debug(guild_id, "suggestions.on_message", f"No suggestion settings found for channel {channel.id}")
                return
            else:
                channel_settings = channel_settings[0]

            log_channel = await self.discord_helper.get_or_fetch_channel(int(channel_settings['log_channel_id']))

            vote_emoji = [ channel_settings["vote_up_emoji"], channel_settings["vote_neutral_emoji"] , channel_settings["vote_down_emoji"] ]
            admin_emoji = [
                channel_settings["admin_approve_emoji"],
                channel_settings["admin_consider_emoji"],
                channel_settings["admin_implemented_emoji"],
                channel_settings["admin_reject_emoji"],
                channel_settings["admin_close_emoji"],
                channel_settings["admin_delete_emoji"]
                ]

            if str(payload.emoji) in vote_emoji:
                # vote up or down
                self.log.debug(guild_id, "suggestions.on_raw_reaction_add", f"{user.name} voted {payload.emoji} on suggestion {suggestion['id']}")

                if str(payload.emoji) == channel_settings["vote_down_emoji"]:
                    vote = -1
                elif str(payload.emoji) == channel_settings["vote_neutral_emoji"]:
                    vote = 0
                else:
                    vote = 1

                has_user_voted = self.db.has_user_voted(suggestion['id'], user.id)
                if has_user_voted:
                    self.log.debug(guild_id, "suggestions.on_raw_reaction_add", f"{user.name} has already voted on suggestion {suggestion['id']}")
                    await message.remove_reaction(payload.emoji, user)
                    await self.discord_helper.sendEmbed(user, "Can only vote once", f"You have already voted on this suggestion.", color=0xff0000, delete_after=30)
                    return
                else:
                    self.db.vote_suggestion_by_id(suggestion['id'], user.id, vote)
                pass
            # if the user reacted with an admin emoji and they are an admin
            elif str(payload.emoji) in admin_emoji and await self.discord_helper.is_admin(guild_id, user.id):
                states = models.SuggestionStates()
                # change the state based on the emoji
                if str(payload.emoji) == channel_settings["admin_approve_emoji"]:
                    self.log.debug(guild_id, "suggestions.on_raw_reaction_add", f"{user.name} approved suggestion {suggestion['id']}")
                    # build ctx to pass to the ask_text function
                    ctx = self.discord_helper.create_context(bot=self.bot, author=user, guild=None, channel=None, message=None)
                    reason = await self.discord_helper.ask_text(ctx, user, "Approve Suggestion", "Please enter a reason for approving this suggestion.", timeout=60) or "No reason given."
                    self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.APPROVED, user.id, reason)
                    await self.close_suggestion(message, states.APPROVED, user, reason, author=author)
                elif str(payload.emoji) == channel_settings["admin_consider_emoji"]:
                    self.log.debug(guild_id, "suggestions.on_raw_reaction_add", f"{user.name} considered suggestion {suggestion['id']}")
                    # build ctx to pass to the ask_text function
                    ctx = self.discord_helper.create_context(bot=self.bot, author=user, guild=None, channel=None, message=None)
                    reason = await self.discord_helper.ask_text(ctx, user, "Consider Suggestion", "Please enter a reason for considering this suggestion.", timeout=60) or "No reason given."
                    self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.CONSIDERED, user.id, reason)
                    await self.close_suggestion(message, states.CONSIDERED, user, reason, author=author)
                elif str(payload.emoji) == channel_settings["admin_implemented_emoji"]:
                    self.log.debug(guild_id, "suggestions.on_raw_reaction_add", f"{user.name} implemented suggestion {suggestion['id']}")
                    # build ctx to pass to the ask_text function
                    ctx = self.discord_helper.create_context(bot=self.bot, author=user, guild=None, channel=None, message=None)
                    reason = await self.discord_helper.ask_text(ctx, user, "Implement Suggestion", "Please enter a reason for implementing this suggestion.", timeout=60) or "No reason given."
                    self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.IMPLEMENTED, user.id, reason)
                    await self.close_suggestion(message, states.IMPLEMENTED, user, reason, author=author)
                elif str(payload.emoji) == channel_settings["admin_reject_emoji"]:
                    self.log.debug(guild_id, "suggestions.on_raw_reaction_add", f"{user.name} rejected suggestion {suggestion['id']}")
                    # build ctx to pass to the ask_text function
                    ctx = self.discord_helper.create_context(bot=self.bot, author=user, guild=None, channel=None, message=None)
                    reason = await self.discord_helper.ask_text(ctx, user, "Reject Suggestion", "Please enter a reason for rejecting this suggestion.", timeout=60) or "No reason given."
                    self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.REJECTED, user.id, reason)
                    await self.close_suggestion(message, states.REJECTED, user, reason, author=author)
                elif str(payload.emoji) == channel_settings["admin_close_emoji"]:
                    # close the suggestion and move it to the archive
                    self.log.debug(guild_id, "suggestions.on_raw_reaction_add", f"{user.name} closed suggestion {suggestion['id']}")
                    # build ctx to pass to the ask_text function
                    ctx = self.discord_helper.create_context(bot=self.bot, author=user, guild=None, channel=None, message=None)
                    reason = await self.discord_helper.ask_text(ctx, user, "Close Suggestion", "Please enter a reason for closing this suggestion.", timeout=60) or "Closed by admin."
                    self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.CLOSED, user.id, reason)
                    await self.close_suggestion(message, states.CLOSED, user, reason, author=author)
                    # move it to the archive channel
                    if log_channel:
                        # add fields with the votes
                        # get the votes from the database
                        votes = self.db.get_suggestion_votes_by_id(suggestion['id'])
                        # get count of each type of vote. either -1, 0, or 1
                        up_votes = [ vote for vote in votes if vote['vote'] == 1 ] or []
                        neutral_votes = [ vote for vote in votes if vote['vote'] == 0 ] or []
                        down_votes = [ vote for vote in votes if vote['vote'] == -1 ] or []
                        remove_fields = [
                            { "name": "Voting" },
                            { "name": "🛡 Actions" }
                        ]
                        # rogelioVzz98 - hosted the channel
                        fields = [
                            { "name": "Votes", "value": f"{channel_settings['vote_up_emoji']} {len(up_votes)} Up Votes\n{channel_settings['vote_neutral_emoji']} {len(neutral_votes)} Neutral Votes\n{channel_settings['vote_down_emoji']} {len(down_votes)} Down Votes" },
                        ]
                        await self.discord_helper.move_message(message, log_channel, author=author, who = user, reason = reason, fields=fields, remove_fields = remove_fields)
                        await message.delete()
                    else:
                        self.log.debug(guild_id, "suggestions.on_raw_reaction_add", f"{user.name} tried to close suggestion {suggestion['id']} but there is no log channel")
                        await self.discord_helper.sendEmbed(user, "No log channel", f"There is no log channel configured. Please make sure `.taco init suggestions` was ran.", color=0xff0000, delete_after=30)
                        # if no log channel. Set status to no longer "answer" to votes.
                        return

            else:
                # unknown emoji. remove it
                await message.remove_reaction(payload.emoji, user)

        except Exception as e:
            self.log.error(guild_id, "trivia", str(e), traceback.format_exc())
            return


    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        _method = inspect.stack()[0][3]
        try:
            guild_id = payload.guild_id
            if guild_id is None or guild_id == 0:
                self.log.debug(0, "suggestions.on_raw_reaction_remove", f"{_method} - guild_id is None or 0")
                return
            if payload.event_type != 'REACTION_REMOVE':
                self.log.debug(guild_id, "suggestions.on_raw_reaction_remove", f"{_method} - payload.event_type != 'REACTION_REMOVE'")
                return
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if user.bot:
                self.log.debug(guild_id, "suggestions.on_raw_reaction_remove", f"{_method} - user.bot")
                return

            # get suggestion from database
            suggestion = self.db.get_suggestion(guild_id, payload.message_id)
            if not suggestion or suggestion['message_id'] != str(payload.message_id):
                self.log.debug(guild_id, "suggestions.on_raw_reaction_remove", f"{user.name} removed reaction to non-existent suggestion")
                return

            author = await self.discord_helper.get_or_fetch_user(int(suggestion['author_id']))
            print(f"author: {author}")

            ss = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not ss:
                # raise exception if there are no suggestion settings
                self.log.debug(guild_id, "suggestions.on_message", f"No suggestion settings found for guild {guild_id}")
                raise Exception("No suggestion settings found")

            channel_settings = [ c for c in ss['channels'] if c['id'] == str(channel.id) ]
            if not channel_settings:
                self.log.debug(guild_id, "suggestions.on_message", f"No suggestion settings found for channel {channel.id}")
                return
            else:
                channel_settings = channel_settings[0]

            vote_emoji = [ channel_settings["vote_up_emoji"], channel_settings["vote_neutral_emoji"], channel_settings["vote_down_emoji"] ]
            admin_emoji = [
                channel_settings["admin_approve_emoji"],
                channel_settings["admin_consider_emoji"],
                channel_settings["admin_implemented_emoji"],
                channel_settings["admin_reject_emoji"]
                # cannot remove the close emoji. It moves the suggestion to the closed state and puts it in the archive
                # channel_settings["admin_close_emoji"],
                # cannot undelete a suggestion
                # channel_settings["admin_delete_emoji"]
                ]

            if str(payload.emoji) in vote_emoji:
                # remove vote
                self.log.debug(guild_id, "suggestions.on_raw_reaction_remove", f"{user.name} removed vote from suggestion {suggestion['id']}")
                has_user_voted = self.db.has_user_voted(suggestion['id'], user.id)
                if not has_user_voted:
                    return
                else:
                    self.db.unvote_suggestion_by_id(guild_id, suggestion['id'], user.id)
            elif str(payload.emoji) in admin_emoji and await self.discord_helper.is_admin(guild_id, user.id):
                states = models.SuggestionStates()

                # admin removed reaction. do we need to set the state back to Active?
                self.log.debug(guild_id, "suggestions.on_raw_reaction_remove", f"{user.name} removed admin reaction from suggestion {suggestion['id']}")
                reject_reactions = [ r.count for r in message.reactions if str(r.emoji) == channel_settings["admin_reject_emoji"] ]
                implemented_reactions = [ r.count for r in message.reactions if str(r.emoji) == channel_settings["admin_implemented_emoji"] ]
                consider_reactions = [ r.count for r in message.reactions if str(r.emoji) == channel_settings["admin_consider_emoji"] ]
                approve_reactions = [ r.count for r in message.reactions if str(r.emoji) == channel_settings["admin_approve_emoji"] ]

                reject_count = len(reject_reactions)
                implemented_count = len(implemented_reactions)
                consider_count = len(consider_reactions)
                approve_count = len(approve_reactions)

                # if denied count is 0, set state back to active
                if str(payload.emoji) == channel_settings["admin_reject_emoji"]:
                    if reject_count <= 0:
                        if implemented_count != 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.IMPLEMENTED, user.id, "Reject State Was Removed")
                            await self.close_suggestion(message, states.IMPLEMENTED, user, "Reject State Was Removed", author=author)
                        elif consider_count != 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.CONSIDERED, user.id, "Reject State Was Removed")
                            await self.close_suggestion(message, states.CONSIDERED, user, "Reject State Was Removed", author=author)
                        elif approve_count != 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.APPROVED, user.id, "Reject State Was Removed")
                            await self.close_suggestion(message, states.APPROVED, user, "Reject State Was Removed", author=author)
                        else:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.ACTIVE, user.id, "Reject State Was Removed")
                            await self.close_suggestion(message, states.ACTIVE, user, "Reject State Was Removed", author=author)
                elif str(payload.emoji) == channel_settings["admin_implemented_emoji"]:
                    if implemented_count <= 0:
                        if reject_count > 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.REJECTED, user.id, "Implemented State Was Removed")
                            await self.close_suggestion(message, states.REJECTED, user, "Implemented State Was Removed", author=author)
                        elif consider_count > 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.CONSIDERED, user.id, "Implemented State Was Removed")
                            await self.close_suggestion(message, states.CONSIDERED, user, "Reject State Was Removed", author=author)
                        elif approve_count > 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.APPROVED, user.id, "Implemented State Was Removed")
                            await self.close_suggestion(message, states.APPROVED, user, "Reject State Was Removed", author=author)
                        else:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.ACTIVE, user.id, "Implemented State Was Removed")
                            await self.close_suggestion(message, states.ACTIVE, user, "Reject State Was Removed", author=author)
                elif str(payload.emoji) == channel_settings["admin_consider_emoji"]:
                    if consider_count <= 0:
                        if reject_count > 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.REJECTED, user.id, "Consider State Was Removed")
                            await self.close_suggestion(message, states.REJECTED, user, "Consider State Was Removed", author=author)
                        elif implemented_count > 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.IMPLEMENTED, user.id, "Consider State Was Removed")
                            await self.close_suggestion(message, states.IMPLEMENTED, user, "Consider State Was Removed", author=author)
                        elif approve_count > 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.APPROVED, user.id, "Consider State Was Removed")
                            await self.close_suggestion(message, states.APPROVED, user, "Consider State Was Removed", author=author)
                        else:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.ACTIVE, user.id, "Consider State Was Removed")
                            await self.close_suggestion(message, states.ACTIVE, user, "Consider State Was Removed", author=author)
                elif str(payload.emoji) == channel_settings["admin_approve_emoji"]:
                    if approve_count <= 0:
                        if reject_count > 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.REJECTED, user.id, "Approve State Was Removed")
                            await self.close_suggestion(message, states.REJECTED, user, "Approve State Was Removed", author=author)
                        elif implemented_count > 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.IMPLEMENTED, user.id, "Approve State Was Removed")
                            await self.close_suggestion(message, states.IMPLEMENTED, user, "Approve State Was Removed", author=author)
                        elif consider_count > 0:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.CONSIDERED, user.id, "Approve State Was Removed")
                            await self.close_suggestion(message, states.CONSIDERED, user, "Approve State Was Removed", author=author)
                        else:
                            self.db.set_state_suggestion_by_id(guild_id, suggestion['id'], states.ACTIVE, user.id, "Approve State Was Removed")
                            await self.close_suggestion(message, states.ACTIVE, user, "Approve State Was Removed", author=author)
            else:
                # unknown emoji. remove it
                pass

        except Exception as e:
            self.log.error(guild_id, "trivia", str(e), traceback.format_exc())
            return

    async def close_suggestion(self, message, state: str, user: discord.User, reason: str, author: discord.User = None):
        if not state:
            return
        states = models.SuggestionStates()
        if not message or len(message.embeds) == 0:
            return
        if state == states.APPROVED:
            color = 0x00ff00
        elif state == states.CONSIDERED:
            color = 0xffff00
        elif state == states.IMPLEMENTED:
            color = 0xaaaaaa
        elif state == states.REJECTED:
            color = 0xff0000
        else: # active
            color = 0x7289da
        # get the date and time now formatted MM/dd/yyyy HH:mm:ss
        now = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        fields = [ {"name": f"{state} @ {now}", "value": f"{user.mention}: {reason}", "inline": False }]
        await self.discord_helper.updateEmbed(message, fields=fields, color=color, author=author)
def setup(bot):
    bot.add_cog(Suggestions(bot))
