import discord
from discord.ext import commands
import traceback
from . import settings
from . import logger
from . import loglevel


class ChannelSelect(discord.ui.Select):
    def __init__(self, ctx, placeholder: str, channels, allow_none: bool = False):
        max_items = 24 if not allow_none else 23
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        self.ctx = ctx

        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        self.log = logger.Log(minimumLogLevel=log_level)
        options = []

        if len(channels) >= max_items:
            # self.log.warn(
            #     ctx.guild.id, _method, f"Guild has more than 24 channels. Total Channels: {str(len(channels))}"
            # )
            options.append(
                discord.SelectOption(label=self.settings.get_string(ctx.guild.id, "other"), value="0", emoji="⏭")
            )
            # sub_message = self.get_string(guild_id, 'ask_admin_role_submessage')
        if allow_none:
            options.append(
                discord.SelectOption(label=self.settings.get_string(ctx.guild.id, "none"), value="-1", emoji="⛔")
            )
        for c in channels[:max_items]:
            self.log.debug(ctx.guild.id, "ChannelSelect.__init__", f"Adding channel {c.name} to options")
            options.append(discord.SelectOption(label=c.name, value=str(c.id), emoji="🏷"))
        self.options = options


class ChannelSelectView(discord.ui.View):
    def __init__(self, ctx, placeholder: str, channels, select_callback=None, timeout_callback=None, allow_none: bool = False, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        self.log = logger.Log(minimumLogLevel=log_level)

        self.ctx = ctx
        self.channel_select = ChannelSelect(ctx, placeholder, channels, allow_none)

        self.timeout_callback = timeout_callback
        async def callback(interaction):
            await interaction.response.defer()
            if select_callback is not None:
                await select_callback(self.channel_select, interaction)
        if select_callback is not None:
            self.channel_select.callback = callback
        self.add_item(self.channel_select)

    async def on_timeout(self):
        self.clear_items()
        if self.timeout_callback is not None:
            await self.timeout_callback()

    async def on_error(self, error, item, interaction):
        self.clear_items()
        self.log.error(self.ctx.guild.id, "ChannelSelectView.on_error", str(error), traceback.format_exc())
