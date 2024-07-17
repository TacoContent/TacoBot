import discord


class ExternalUrlButtonView(discord.ui.View):
    def __init__(self, label: str, url: str):
        super().__init__()
        self.add_item(ExternalUrlButton(label=label, url=url))

class ExternalUrlButton(discord.ui.Button):
    def __init__(self, label: str, url: str):
        super().__init__(label=label, style=discord.ButtonStyle.link, url=url)
