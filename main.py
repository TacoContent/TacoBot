import asyncio
import functools
import time
import os
import signal
from concurrent.futures import ProcessPoolExecutor

from httpserver import HttpServer
import asyncio

import bot.tacobot as bot
import discord
from bot.cogs.lib.colors import Colors
from bot.cogs.lib.mongodb.migration_runner import MigrationRunner
from dotenv import find_dotenv, load_dotenv
from webhook.listener import WebhookListener
from metrics.exporter import MetricsExporter


load_dotenv(find_dotenv())

def sighandler(signum, frame):
    print(Colors.colorize(Colors.FGYELLOW, "<SIGTERM received>"))
    exit(0)

def init_tacobot() -> bot.TacoBot:
    intents = discord.Intents.all()
    intents.message_content = True
    intents.members = True
    intents.presences = True
    intents.guilds = True
    intents.guild_messages = True
    intents.guild_reactions = True
    tbot = bot.TacoBot(intents=intents)
    return tbot

def start_tacobot():
    try:
        DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

        migrations = MigrationRunner()
        migrations.start_migrations()

        tacobot = init_tacobot()

        tacobot.run(DISCORD_TOKEN)


    except KeyboardInterrupt:
        print(Colors.colorize(Colors.FGYELLOW, "<KeyboardInterrupt received>"))
        exit(0)


def exporter():
    try:
        exporter = MetricsExporter()
        exporter.run()
    except KeyboardInterrupt:
        print(Colors.colorize(Colors.FGYELLOW, "<KeyboardInterrupt received>"))
        exit(0)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    signal.signal(signal.SIGTERM, sighandler)
    try:
        executor = ProcessPoolExecutor(2)

        loop.run_in_executor(executor, start_tacobot)
        loop.run_in_executor(executor, exporter)

        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
