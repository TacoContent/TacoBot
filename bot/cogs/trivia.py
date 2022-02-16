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
        self.log.debug(0, "trivia.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "trivia.__init__", f"Logger initialized with level {log_level.name}")

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

    @commands.group(name="trivia", invoke_without_command=True)
    async def trivia(self, ctx: ComponentContext):
        try:
            if ctx.invoked_subcommand is None:
                guild_id = 0
                if ctx.guild:
                    guild_id = ctx.guild.id
                    await ctx.message.delete()
                else:
                    self.log.warning(guild_id, "trivia", "Cannot run trivia command in DM")
                    return

                channel_id = ctx.channel.id

                trivia_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
                if not trivia_settings:
                    # log error if there are no tacos settings
                    self.log.error(guild_id, "trivia.trivia", "No trivia settings found")
                    self.discord_helper.notify_bot_not_initialized(ctx, "trivia")
                    return

                allowed_channels = trivia_settings["allowed_channels"]
                if allowed_channels and str(channel_id) not in allowed_channels:
                    # log that the user tried to use the command in a channel that is not allowed
                    self.log.debug(guild_id, "trivia.trivia", f"User {ctx.author.name}#{ctx.author.discriminator} tried to use the trivia command in channel {channel_id}")
                    return

                # start trivia
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
                    taco_word = "taco" if reward == 1 else "tacos"
                    trivia_timeout = trivia_settings['timeout'] or 60

                    question_message = f"{html.unescape(question.question)}\n\n{choice_message}\n\nReact with the correct answer. Only your first answer counts.\n\nYou have {trivia_timeout} seconds to answer"
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
                                if user.bot or user.id in [ r.users for r in ctx.message.reactions ] or user.id in [ u.id for u in correct_users ] or user.id in [ u.id for u in incorrect_users ]:
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

                            await self.discord_helper.sendEmbed(ctx.channel,
                                "Trivia - Results",
                                f"{html.unescape(question.question)}\n\nThe correct answer was **{choice_emojis[correct_index]} {html.unescape(answers[correct_index])}**\n\nCorrect answers receive {reward} {taco_word} 🌮.\n\n`.taco trivia` to play again.",
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