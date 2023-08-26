import asyncio
import bot.tacobot as bot
import discord
import os
import signal

from bot.cogs.lib.migration_runner import MigrationRunner
from concurrent.futures import ProcessPoolExecutor
from dotenv import load_dotenv, find_dotenv
from metrics.exporter import MetricsExporter


load_dotenv(find_dotenv())


def sighandler(signum, frame):
    print("<SIGTERM received>")
    exit(0)


def main():
    try:
        DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

        migrations = MigrationRunner()
        migrations.start_migrations()

        intents = discord.Intents.all()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True

        tacobot = bot.TacoBot(intents=intents)
        tacobot.remove_command('help')
        tacobot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("<KeyboardInterrupt received>")
        exit(0)


def exporter():
    try:
        pass
        exporter = MetricsExporter()
        exporter.run()
    except KeyboardInterrupt:
        print("<KeyboardInterrupt received>")
        exit(0)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    signal.signal(signal.SIGTERM, sighandler)
    try:
        executor = ProcessPoolExecutor(2)
        loop.run_in_executor(executor, main)
        loop.run_in_executor(executor, exporter)
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
