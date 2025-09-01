import asyncio
import atexit
import os
import signal
from concurrent.futures import ProcessPoolExecutor

if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import bot.tacobot as bot
import discord
from bot.lib.colors import Colors
from bot.lib.mongodb.migration_runner import MigrationRunner
from bot.lib.mongodb.mongo_singleton import MongoClientSingleton
from dotenv import find_dotenv, load_dotenv
from metrics.exporter import MetricsExporter

load_dotenv(find_dotenv())
atexit.register(MongoClientSingleton.close_client)


def sighandler(signum, frame):
    print(Colors.colorize(Colors.FGYELLOW, "<SIGTERM received>"))


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


def exporter():
    try:
        exporter = MetricsExporter()
        exporter.run()
    except KeyboardInterrupt:
        print(Colors.colorize(Colors.FGYELLOW, "<KeyboardInterrupt received>"))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    signal.signal(signal.SIGTERM, sighandler)
    executor = ProcessPoolExecutor(2)
    try:
        loop.run_in_executor(executor, start_tacobot)
        loop.run_in_executor(executor, exporter)

        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown(wait=True)  # Ensure all processes are cleaned up
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        try:
            loop.run_until_complete(loop.shutdown_default_executor())
        except Exception:
            pass
        loop.close()
        try:
            from bot.lib.mongodb.mongo_singleton import MongoClientSingleton

            MongoClientSingleton.close_client()
        except ImportError:
            pass
