import asyncio
import collections
import html
import inspect
import os
import random
import requests
import traceback
import typing

from bot.cogs.lib import (
    discordhelper,
    logger,
    loglevel,
    mongo,
    settings,
    utils,
    tacotypes,
)  # pylint: disable=no-name-in-module
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.models import TriviaQuestion
from discord.ext import commands
from discord.ext.commands import Context


class Trivia(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.SETTINGS_SECTION = "trivia"
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.CATEGORY_POINTS_DEFAULTS = {"hard": 15, "medium": 10, "easy": 5}
        self.CHOICE_EMOJIS_DEFAULTS = ['🇦', '🇧', '🇨', '🇩']
        self.TRIVIA_TIMEOUT_DEFAULT = 60

        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            self.log.debug(0, f"{self._module}.{self._class}.{_method}", "trivia cog is ready")
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.group(name="trivia", invoke_without_command=True)
    @commands.guild_only()
    async def trivia(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.invoked_subcommand is None:
                if ctx.guild:
                    guild_id = ctx.guild.id
                    if ctx.message:
                        await ctx.message.delete()
                else:
                    self.log.warn(
                        guild_id, f"{self._module}.{self._class}.{_method}", "Cannot run trivia command in DM"
                    )
                    return

                channel_id = ctx.channel.id

                cog_settings = self.get_cog_settings(guild_id)

                allowed_channels = cog_settings.get("allowed_channels", None)
                if allowed_channels and str(channel_id) not in allowed_channels:
                    # log that the user tried to use the command in a channel that is not allowed
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"User {utils.get_user_display_name(ctx.author)} tried to use the trivia command in channel {channel_id}",
                    )
                    return

                question = self.get_question(ctx)
                if question:
                    choice_emojis = cog_settings.get("choices", self.CHOICE_EMOJIS_DEFAULTS)

                    # get incorrect answers unescaped and add them to the list
                    answers = [html.unescape(ia) for ia in question.incorrect_answers]
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

                    # get the reward and punishment
                    reward = cog_settings.get('category_points', self.CATEGORY_POINTS_DEFAULTS).get(
                        question.difficulty, 5
                    )
                    punishment = reward * -1

                    taco_word = (
                        self.settings.get_string(guild_id, "taco_singular")
                        if reward == 1
                        else self.settings.get_string(guild_id, "taco_plural")
                    )
                    trivia_timeout = cog_settings.get('timeout', self.TRIVIA_TIMEOUT_DEFAULT)

                    notify_role_id = cog_settings.get('notify_role', None)
                    notify_role_mention = None
                    if notify_role_id:
                        notify_role = ctx.guild.get_role(int(notify_role_id))
                        if notify_role:
                            notify_role_mention = f"{notify_role.mention}"

                    question_message = self.settings.get_string(
                        guild_id,
                        "trivia_question",
                        question=html.unescape(question.question),
                        choice_message=choice_message,
                        trivia_timeout=trivia_timeout,
                        reward=reward,
                        taco_word=taco_word,
                    )

                    qm = await self.messaging.send_embed(
                        channel=ctx.channel,
                        title=self.settings.get_string(
                            guild_id,
                            "trivia_question_title",
                            category=html.unescape(question.category),
                            difficulty=question.difficulty.capitalize(),
                            reward=reward,
                        ),
                        message=question_message,
                        fields=[],
                        content=notify_role_mention if notify_role_mention else None,
                    )

                    for ritem in choice_emojis[0 : len(answers)]:
                        # add reaction to the message from the bot
                        await qm.add_reaction(ritem)
                    await asyncio.sleep(1)
                    while True:
                        try:
                            available_choices = choice_emojis[0 : len(answers)]

                            def check(reaction, user):
                                # check if user already reacted
                                # or if the user.id is in the correct or incorrect list of users
                                if (
                                    user.bot
                                    or user.id in [r.users for r in qm.reactions]
                                    or user.id in [u.id for u in correct_users]
                                    or user.id in [u.id for u in incorrect_users]
                                ):
                                    return False

                                if reaction.emoji in available_choices:
                                    if reaction.emoji == choice_emojis[correct_index]:
                                        correct_users.append(user)
                                    else:
                                        incorrect_users.append(user)
                                    return True

                            reaction, user = await self.bot.wait_for(
                                'reaction_add', timeout=trivia_timeout, check=check
                            )
                        except asyncio.TimeoutError:
                            correct_list = '\n'.join([u.mention for u in correct_users])
                            incorrect_list = '\n'.join([u.mention for u in incorrect_users])
                            no_one = self.settings.get_string(guild_id, "no_one")
                            # fields = [
                            #     { "name": self.settings.get_string(guild_id, "correct"), "value": f"{correct_list or no_one}", "inline": True },
                            #     { "name": self.settings.get_string(guild_id, "incorrect"), "value": f"{incorrect_list or no_one}", "inline": True },
                            # ]
                            fields = [
                                {
                                    "name": self.settings.get_string(guild_id, "correct"),
                                    "value": f"{correct_list or no_one}",
                                    "inline": True,
                                },
                                {
                                    "name": self.settings.get_string(guild_id, "incorrect"),
                                    "value": f"{incorrect_list or no_one}",
                                    "inline": True,
                                },
                            ]
                            # add tacos to the correct users
                            reason_msg = self.settings.get_string(guild_id, "taco_reason_trivia_correct")
                            for u in correct_users:
                                if not u.bot:
                                    await self.discord_helper.taco_give_user(
                                        guildId=guild_id,
                                        fromUser=self.bot.user,
                                        toUser=u,
                                        reason=reason_msg,
                                        give_type=tacotypes.TacoTypes.TRIVIA_CORRECT,
                                        taco_amount=reward,
                                    )

                            reason_msg = self.settings.get_string(guild_id, "taco_reason_trivia_incorrect")
                            for u in incorrect_users:
                                if not u.bot:
                                    await self.discord_helper.taco_give_user(
                                        guildId=guild_id,
                                        fromUser=self.bot.user,
                                        toUser=u,
                                        reason=reason_msg,
                                        give_type=tacotypes.TacoTypes.TRIVIA_INCORRECT,
                                        taco_amount=punishment,
                                    )

                            result = await self.messaging.send_embed(
                                channel=ctx.channel,
                                title=self.settings.get_string(guild_id, "trivia_results_title"),
                                message=self.settings.get_string(
                                    guild_id,
                                    "trivia_results_message",
                                    question=html.unescape(question.question),
                                    correct_emoji=choice_emojis[correct_index],
                                    correct_answer=html.unescape(answers[correct_index]),
                                    reward=reward,
                                    taco_word=taco_word,
                                ),
                                fields=fields,
                            )
                            await qm.delete()

                            # now that we have the question message, we can track the trivia item in the database
                            trivia_item = {
                                "guild_id": guild_id,
                                "channel_id": ctx.channel.id,
                                "message_id": result.id,
                                "starter_id": ctx.author.id,
                                "question": html.unescape(question.question),
                                "correct_answer": html.unescape(question.correct_answer),
                                "incorrect_answers": [html.unescape(ia) for ia in question.incorrect_answers],
                                "category": html.unescape(question.category),
                                "difficulty": question.difficulty,
                                "reward": reward,
                                "punishment": punishment,
                                "correct_users": [u.id for u in correct_users],
                                "incorrect_users": [u.id for u in incorrect_users],
                            }

                            trivia_question = TriviaQuestion(**trivia_item)
                            self.db.track_trivia_question(trivia_question)
                            break
                else:
                    self.log.error(
                        guild_id, f"{self._module}.{self._class}.{_method}", "Error retrieving the trivia question"
                    )
            else:
                pass
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    def get_question(self, ctx: Context) -> typing.Any:
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id
            else:
                return None

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                # raise exception if there are no tacos settings
                raise Exception("No trivia settings found")

            url = cog_settings.get('api_url', "").format("", "", "")
            if not url:
                raise Exception("No trivia api url found")

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
    await bot.add_cog(Trivia(bot))
