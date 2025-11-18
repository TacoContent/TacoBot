import inspect
import os

import discord
from bot.lib import logger
from bot.lib.enums import loglevel
from bot.lib.settings import Settings


class PullTabTicketRedeemView(discord.ui.View):
    """Discord UI View for redeeming pulltab tickets."""

    def __init__(self, ctx, *, code: str, multiplier: int = 1, timeout: int = 180, settings: Settings, cog):
        super().__init__(timeout=timeout)
        _method = inspect.stack()[0][3]
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings

        log_level = loglevel.LogLevel.DEBUG
        try:
            log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        except Exception:
            pass
        self.log = logger.Log(minimumLogLevel=log_level)

        self.guild_id = ctx.guild.id if ctx.guild is not None else 0
        self.ctx = ctx

        self.ctx = ctx
        self.multiplier = multiplier
        self.code = code
        self.cog = cog
        redeem_button = self._create_redeem_button(code=code)
        buy_button = self._create_buy_button(multiplier=multiplier)
        self.add_item(redeem_button)
        self.add_item(buy_button)

    def _create_redeem_button(self, *, code: str) -> discord.ui.Button:
        """Create a Discord button for redeeming a pulltab ticket."""
        button = discord.ui.Button(
            label="Redeem Ticket", style=discord.ButtonStyle.primary, custom_id=f"pulltab_redeem:{code}"
        )
        button.callback = self._on_redeem_button_click
        return button

    def _create_buy_button(self, *, multiplier: int) -> discord.ui.Button:
        """Create a Discord button for redeeming a pulltab ticket."""
        button = discord.ui.Button(label=f"Buy Ticket ({multiplier}x multiplier)", style=discord.ButtonStyle.green)
        button.callback = self._on_buy_button_click
        return button

    async def _on_buy_button_click(self, interaction: discord.Interaction):
        """Handle the buy button click."""
        await self.cog._process_pulltab_purchase(interaction, multiplier=self.multiplier)

    async def _on_redeem_button_click(self, interaction: discord.Interaction):
        """Handle the redeem button click."""
        await self.cog._process_pulltab_redeem(interaction, code=self.code)
        if self.children and len(self.children) > 1:
            # update the view to disable buttons after redeeming
            self.remove_item(self.children[0])  # Remove redeem button
