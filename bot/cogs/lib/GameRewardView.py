import discord
from discord.ext import commands
import traceback
import inspect
import os

from . import settings
from . import logger
from . import loglevel
import typing


class GameRewardView(discord.ui.View):
    def __init__(
        self,
        ctx,
        game_id: str,
        claim_callback: typing.Optional[typing.Callable] = None,
        timeout_callback: typing.Optional[typing.Callable] = None,
        cost: int = 500,
        timeout: int = 60 * 60 * 24,
    ):
        super().__init__(timeout=timeout)
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]

        guild_id = ctx.guild.id if ctx.guild is not None else 0
        self.ctx = ctx

        self.log = logger.Log(minimumLogLevel=log_level)

        if cost == 1:
            tacos_word = self.settings.get_string(guild_id, "taco_singular")
        else:
            tacos_word = self.settings.get_string(guild_id, "taco_plural")

        self.timeout_callback = timeout_callback

        self.claim_button = discord.ui.Button(
            custom_id=game_id,
            label=self.settings.get_string(ctx.guild.id, "game_key_claim_button", tacos=cost, tacos_word=tacos_word),
            style=discord.ButtonStyle.green,
        )
        self.claim_button_callback = claim_callback
        self.claim_button.callback = self.claim_callback
        self.add_item(self.claim_button)
        pass

    async def claim_callback(self, interaction: discord.Interaction) -> None:
        # check if the user who clicked the button is the same as the user who started the command
        if interaction.user.id != self.ctx.author.id:
            return
        await interaction.response.defer()
        if self.claim_button_callback is not None:
            await self.claim_button_callback(interaction)
            self.stop()

    async def on_timeout(self) -> None:
        if self.timeout_callback is not None:
            await self.timeout_callback()
        pass

    async def on_error(self, error, item, interaction) -> None:
        _method = inspect.stack()[0][3]
        self.log.error(self.ctx.guild.id, f"{self._module}.{_method}", str(error), traceback.format_exc())
