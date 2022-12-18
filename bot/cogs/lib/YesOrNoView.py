import discord
from discord.ext import commands
import traceback
from . import settings
from . import logger
from . import loglevel
import typing
from . import utils

class YesOrNoView(discord.ui.View):
    def __init__(
        self,
        ctx,
        answer_callback: typing.Callable = None,
        timeout_callback: typing.Callable = None,
        timeout: int = 60 * 5,
    ):
        super().__init__(timeout=timeout)
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        self.ctx = ctx
        guild_id = ctx.guild.id if ctx.guild is not None else 0

        self.log = logger.Log(minimumLogLevel=log_level)

        self.timeout_callback = timeout_callback

        self.yes_button = discord.ui.Button(
            custom_id="YES", label=self.settings.get_string(ctx.guild.id, "yes"), style=discord.ButtonStyle.green
        )
        self.button_answer_callback = answer_callback
        # set to our internal callback
        self.yes_button.callback = self.answer_callback
        self.add_item(self.yes_button)

        self.no_button = discord.ui.Button(
            custom_id="NO", label=self.settings.get_string(ctx.guild.id, "no"), style=discord.ButtonStyle.red
        )
        # set to our internal callback
        self.no_button.callback = self.answer_callback
        self.add_item(self.no_button)

    async def answer_callback(self, interaction: discord.Interaction):
        # check if the user who clicked the button is the same as the user who started the command
        if interaction.user.id != self.ctx.author.id:
          return
        await interaction.response.defer()

        await interaction.delete_original_response()
        if self.button_answer_callback is not None:
            await self.button_answer_callback(self, interaction)

    async def on_timeout(self, interaction: discord.Interaction):
        self.clear_items()
        if self.timeout_callback is not None:
            await self.timeout_callback(self)

    async def on_error(self, error, item, interaction):
        self.log.error(self.ctx.guild.id, "YesOrNoView.on_error", str(error), traceback.format_exc())
