import typing
from dataclasses import dataclass

import discord
from discord.ext import commands


@dataclass
class InteractionContext:
    bot: commands.Bot
    author: typing.Union[discord.User, discord.Member, discord.ClientUser]
    channel: typing.Union[discord.TextChannel, discord.DMChannel]
    message: discord.Message
    guild: discord.Guild
