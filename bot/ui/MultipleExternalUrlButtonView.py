import discord
from bot.ui.ExternalUrlButtonView import ExternalUrlButton


class ButtonData:
    def __init__(self, label: str, url: str):
        self.label = label
        self.url = url


class MultipleExternalUrlButtonView(discord.ui.View):
    def __init__(self, buttons: list[ButtonData]):
        super().__init__()
        for button in buttons:
            self.add_item(ExternalUrlButton(label=button.label, url=button.url))
