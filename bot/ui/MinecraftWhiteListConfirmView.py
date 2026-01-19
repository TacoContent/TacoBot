import typing
import discord


class MinecraftWhiteListConfirmView(discord.ui.View):
    def __init__(self, *, cog, uuid: str, username: str):
        super().__init__()

        YES = self._create_button(label="YES", style=discord.ButtonStyle.green, callback=self._on_yes_click)
        NO = self._create_button(label="NO", style=discord.ButtonStyle.red, callback=self._on_no_click)

        self.cog = cog

        self.uuid = uuid
        self.username = username

        self.add_item(YES)
        self.add_item(NO)

    async def _on_yes_click(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Handle the "Yes" confirmation logic here
        await self.cog._handle_whitelist_user_confirmation(
            ctx=interaction,
            username=self.username,
            uuid=self.uuid
        )
        await interaction.followup.send("You have been whitelisted!", ephemeral=True)

        await self.cog._minecraft_status(interaction)

    async def _on_no_click(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Handle the "No" confirmation logic here
        await interaction.followup.send("Okay! Please run the command again with the correct username.", ephemeral=True)

    def _create_button(self, label: str, style: discord.ButtonStyle, callback: typing.Callable) -> discord.ui.Button:
        button = discord.ui.Button(
            label=label,
            style=style,
            disabled=False,
        )
        button.callback = callback
        return button
