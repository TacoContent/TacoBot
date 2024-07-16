import discord

class FreeGameUrlButtonView(discord.ui.View):
    def __init__(self, label:str, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label=f"{label}", style=discord.ButtonStyle.link, url=url))
