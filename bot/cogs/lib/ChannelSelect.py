import discord
from discord.ext import commands


class ChannelSelect(discord.ui.Select):
  def __init__(self, ctx, placeholder: str, channels, allow_none: bool = False):
    max_items = 24 if not allow_none else 23
    super().__init__(placeholder=placeholder, min_values=1, max_values=1)
    self.ctx = ctx
    options = []

    if len(channels) >= max_items:
      # self.log.warn(
      #     ctx.guild.id, _method, f"Guild has more than 24 channels. Total Channels: {str(len(channels))}"
      # )
      options.append(
          discord.SelectOption(label=self.ctx.settings.get_string(ctx.guild.id, "other"), value="0", emoji="⏭")
      )
      # sub_message = self.get_string(guild_id, 'ask_admin_role_submessage')
    if allow_none:
      options.append(
          discord.SelectOption(label=self.ctx.settings.get_string(ctx.guild.id, "none"), value="-1", emoji="⛔")
      )
    for c in channels[:max_items]:
      options.append(discord.SelectOption(label=c.name, value=str(c.id), emoji="🏷"))

  async def callback(self, interaction: discord.Interaction):
    await interaction.response.send_message(content=f"Your choice is {self.values[0]}!",ephemeral=True)

class ChannelSelectView(discord.ui.View):
    def __init__(self, ctx, placeholder: str, channels, allow_none: bool = False, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.channel_select = ChannelSelect(ctx, placeholder, channels, allow_none)
        self.add_item(self.channel_select)
