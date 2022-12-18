import discord
from discord.ext import commands
import traceback
from . import settings
from . import logger
from . import loglevel


class GameRewardView(discord.ui.View):
  def __init__(self, ctx, game_id: str, claim_callback = None, timeout_callback = None, cost: int = 500, timeout: int = 60 * 60 * 24):
    super().__init__(timeout=timeout)
    self.settings = settings.Settings()
    log_level = loglevel.LogLevel[self.settings.log_level.upper()]

    guild_id = ctx.guild.id if ctx.guild is not None else 0

    self.log = logger.Log(minimumLogLevel=log_level)

    if cost == 1:
      tacos_word = self.settings.get_string(guild_id, "taco_singular")
    else:
      tacos_word = self.settings.get_string(guild_id, "taco_plural")

    self.timeout_callback = timeout_callback

    self.claim_button = discord.ui.Button(
      custom_id=game_id,
      label=self.settings.get_string(
        ctx.guild.id,
        "game_key_claim_button",
        tacos=cost,
        tacos_word=tacos_word
      ),
      style=discord.ButtonStyle.green
    )
    self.claim_button.callback = claim_callback
    self.add_item(self.claim_button)
    pass

  async def on_timeout(self):
    if self.timeout_callback is not None:
      await self.timeout_callback(self)
    pass

    async def on_error(self, error, item, interaction):
      self.log.error(self.ctx.guild.id, "GameRewardView.on_error", str(error), traceback.format_exc())
