import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import random
import inspect
import requests
from types import SimpleNamespace
import collections
import html

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
from .lib import settings
from .lib import mongo
from .lib import dbprovider

class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.SETTINGS_SECTION = "trivia"
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "trivia.__init__", "Initialized")

        # self.bot.loop.create_task(self.trivia_init())
    # async def trivia_init(self):
    #     await self.bot.wait_until_ready()
    #     channel = await self.discord_helper.get_or_fetch_channel(935318426677825536)
    #     while not self.bot.is_closed:
    #         time = random.randint(60,300)
    #         chance = random.randint(1,1)
    #         if chance == 1:
    #             await self.run_trivia(channel)

    #         await asyncio.sleep(time)

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.log.debug(0, "trivia.on_ready", "trivia cog is ready")
            # get all the guilds that the bot is in
            # guilds = self.bot.guilds

            # for g in guilds:
            #     guild_id = g.id
            #     self.log.debug(guild_id, "trivia.on_ready", f"guild ready {g.name}:{g.id}")
            #     ts = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            #     if not ts:
            #         # raise exception if there are no trivia settings
            #         self.log.debug(guild_id, "trivia.on_ready", f"No trivia settings found for guild {guild_id}")
            #         continue

            #     # get all the trivia channels
            #     while True:
            #         for c in [ c for c in ts['allowed_channels'] ]:
            #             channel = await self.bot.fetch_channel(int(c))
            #             if not channel:
            #                 self.log.debug(guild_id, "trivia.on_ready", f"Channel {c} not found")
            #                 continue

            #             # build ctx to pass to the ask_text function
            #             ctx = self.discord_helper.create_context(bot=self.bot, author=None, guild=g, channel=channel, message=None, invoked_subcommand=None)
            #             await self.discord_helper.wait_for_user_invoke_cleanup(ctx)

            #             create_context = await self.discord_helper.wait_for_user_invoke(ctx, channel, "Looking for a trivia question?", "Click the `Start Trivia` button below.", button_label = "Start Trivia", button_id = "CREATE_TRIVIA_QUESTION")

            #             if create_context:
            #                 self.log.debug(guild_id, "trivia.on_ready", f"trivia invoked: {create_context.author}")
            #                 ctx = self.discord_helper.create_context(bot=self.bot, author=create_context.author, guild=g, channel=channel, message=None, invoked_subcommand=None)

            #                 await self.trivia(ctx)
            #                 # create the trivia question


        except Exception as e:
            self.log.error(0, "trivia.on_ready", str(e), traceback.format_exc())


    @commands.group(name="trivia", invoke_without_command=True)
    async def trivia(self, ctx: ComponentContext):
        try:
            if ctx.invoked_subcommand is None:
                guild_id = 0
                if ctx.guild:
                    guild_id = ctx.guild.id
                    if ctx.message:
                        await ctx.message.delete()
                else:
                    self.log.warning(guild_id, "trivia", "Cannot run trivia command in DM")
                    return

                channel_id = ctx.channel.id

                trivia_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
                if not trivia_settings:
                    # log error if there are no tacos settings
                    self.log.error(guild_id, "trivia.trivia", "No trivia settings found")
                    await self.discord_helper.notify_bot_not_initialized(ctx, "trivia")
                    return

                allowed_channels = trivia_settings["allowed_channels"]
                if allowed_channels and str(channel_id) not in allowed_channels:
                    # log that the user tried to use the command in a channel that is not allowed
                    self.log.debug(guild_id, "trivia.trivia", f"User {ctx.author.name}#{ctx.author.discriminator} tried to use the trivia command in channel {channel_id}")
                    return

                # # start trivia
                # ctx_ = self.discord_helper.create_context(bot=self.bot, author=ctx.author, guild=ctx.guild, channel=ctx.channel, message=ctx.message, invoked_subcommand=None)
                # await self.discord_helper.wait_for_user_invoke_cleanup(ctx_)


                question = self.get_question(ctx)
                if question:

                    choice_emojis = trivia_settings["choices"]

                    print(f"{question.category} {question.difficulty} {question.type} {question.question}")
                    # get incorrect answers unescaped and add them to the list
                    answers = [ html.unescape(ia) for ia in question.incorrect_answers ]
                    # get correct answer unescaped and add it to the list
                    answers.append(html.unescape(question.correct_answer))
                    # if not a boolean question, shuffle the answers
                    if question.type != "boolean":
                        random.shuffle(answers)
                    else:
                        answers = ["True", "False"]
                    correct_index = answers.index(html.unescape(question.correct_answer))

                    choices = []
                    correct_users = []
                    incorrect_users = []
                    for answer in answers:
                        # get the index of the answer
                        index = answers.index(answer)
                        choices.append(f"{choice_emojis[index]} **{answer}**")
                    choice_message = '\n'.join(choices)

                    reward = trivia_settings['category_points'][question.difficulty] or 1
                    punishment = reward * -1
                    taco_word = "taco" if reward == 1 else "tacos"
                    trivia_timeout = trivia_settings['timeout'] or 60

                    notify_role_id = trivia_settings['notify_role']
                    notify_role_mention = ""
                    if notify_role_id:
                        notify_role = ctx.guild.get_role(int(notify_role_id))
                        if notify_role:
                            notify_role_mention = f"{notify_role.mention}"

                    question_message = f"{html.unescape(question.question)}\n\n{choice_message}\n\nReact with the correct answer. Only your first answer counts.\n\nYou have {trivia_timeout} seconds to answer.\nYou will be rewarded **{reward} {taco_word}** for answering correctly.\nYou will lose **{reward} {taco_word}** for answering incorrectly.\n\n{notify_role_mention}"
                    qm = await self.discord_helper.sendEmbed(ctx.channel,
                        f"Trivia - {html.unescape(question.category)} - {question.difficulty.capitalize()} - {reward} 🌮",
                        question_message,
                        fields=[])
                    for ritem in choice_emojis[0:len(answers)]:
                        # add reaction to the message from the bot
                        await qm.add_reaction(ritem)
                    await asyncio.sleep(1)
                    while True:
                        try:
                            available_choices = choice_emojis[0:len(answers)]
                            def check (reaction, user):
                                # check if user already reacted
                                # or if the user.id is in the correct or incorrect list of users
                                if user.bot or user.id in [ r.users for r in qm.reactions ] or user.id in [ u.id for u in correct_users ] or user.id in [ u.id for u in incorrect_users ]:
                                    return False

                                if reaction.emoji in available_choices:
                                    if reaction.emoji == choice_emojis[correct_index]:
                                        correct_users.append(user)
                                    else:
                                        incorrect_users.append(user)
                                    return True
                            reaction, user = await self.bot.wait_for('reaction_add', timeout=trivia_timeout, check=check)
                        except asyncio.TimeoutError:
                            correct_list = '\n'.join([ u.mention for u in correct_users ])
                            incorrect_list = '\n'.join([ u.mention for u in incorrect_users ])
                            fields = [
                                { "name": "Correct", "value": f"{correct_list or 'No one'}", "inline": True },
                                { "name": "Incorrect", "value": f"{incorrect_list or 'No one'}", "inline": True },
                            ]
                            # add tacos to the correct users
                            reason_msg = "Getting trivia question correct"
                            for u in correct_users:
                                if not u.bot:
                                    taco_count = self.db.add_tacos(guild_id, u.id, reward)
                                    await self.discord_helper.tacos_log(guild_id, u, self.bot.user, reward, taco_count, reason_msg)
                            reason_msg = "Getting trivia question incorrect"
                            for u in incorrect_users:
                                if not u.bot:
                                    taco_count = self.db.add_tacos(guild_id, u.id, punishment)
                                    await self.discord_helper.tacos_log(guild_id, u, self.bot.user, punishment, taco_count, reason_msg)

                            await self.discord_helper.sendEmbed(ctx.channel,
                                "Trivia - Results",
                                f"{html.unescape(question.question)}\n\nThe correct answer was **{choice_emojis[correct_index]} {html.unescape(answers[correct_index])}**\n\nCorrect answers receive {reward} {taco_word} 🌮.\nIncorrect answers lose {reward} {taco_word} 🌮.\n\n`.taco trivia` to play again.",
                                fields=fields)
                            await qm.delete()
                            break
                else:
                    print(f"Error getting question")
            else:
                pass
        except Exception as e:
            self.log.error(guild_id, "trivia", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    # async def on_message_delete(self, message):
    #     try:
    #         self.log.debug(0, "trivia.on_ready", "trivia cog is ready")
    #         if not message:
    #              return
    #         if not message.channel:
    #             return
    #         # get all the guilds that the bot is in
    #         guild = message.guild
    #         guild_id = guild.id
    #         ts = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
    #         if not ts:
    #             # raise exception if there are no trivia settings
    #             self.log.debug(guild_id, "trivia.on_message_delete", f"No trivia settings found for guild {guild_id}")
    #             return

    #         channel = message.channel
    #         if str(channel.id) not in ts["allowed_channels"]:
    #             known_invokes = self.db.get_wait_invokes(guildId=guild_id, channelId=channel.id)
    #             if not known_invokes:
    #                 return
    #             filtered_invokes = [ ki['message_id'] for ki in known_invokes if ki['message_id'] == str(message.id)]
    #             if not filtered_invokes or len(filtered_invokes) == 0:
    #                 return


    #             # build ctx to pass to the ask_text function
    #             ctx = self.discord_helper.create_context(bot=self.bot, author=None, guild=guild, channel=channel, message=None, invoked_subcommand=None)
    #             # await self.discord_helper.wait_for_user_invoke_cleanup(ctx)

    #             create_context = await self.discord_helper.wait_for_user_invoke(ctx, channel, "Looking for a trivia question?", "Click the `Start Trivia` button below.", button_label = "Start Trivia", button_id = "CREATE_TRIVIA_QUESTION")

    #             if create_context:
    #                 self.log.debug(guild_id, "trivia.on_ready", f"trivia invoked: {create_context.author}")
    #                 ctx = self.discord_helper.create_context(bot=self.bot, author=create_context.author, guild=g, channel=channel, message=None, invoked_subcommand=None)
    #                 await self.trivia(ctx)
    #                 # create the trivia question


        except Exception as e:
            self.log.error(0, "trivia.on_ready", str(e), traceback.format_exc())

    def get_question(self, ctx: ComponentContext):
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id
            else:
                return None

            trivia_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not trivia_settings:
                # raise exception if there are no tacos settings
                raise Exception("No trivia settings found")

            url = trivia_settings['api_url'].format("", "", "")
            response = requests.get(url)
            data = response.json()
            if data["response_code"] == 0:
                # {
                #   "category":"History",
                #   "type":"multiple",
                #   "difficulty":"easy",
                #   "question":"When was Google founded?",
                #   "correct_answer":"September 4, 1998",
                #   "incorrect_answers":[
                #       "October 9, 1997",
                #       "December 12, 1989",
                #       "Feburary 7th, 2000"
                #   ]
                # }
                dict = data["results"][0]
                x = collections.namedtuple("TriviaQuestion", dict.keys())(*dict.values())
                return x
            else:
                return None
        except Exception as e:
            self.log.error(guild_id, "trivia", str(e), traceback.format_exc())
            return None

def setup(bot):
    bot.add_cog(Trivia(bot))
