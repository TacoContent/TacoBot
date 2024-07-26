import inspect
import os
import traceback
from importlib import import_module

from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.tacobot import TacoBot
from discord.ext import commands
from httpserver.server import HttpServer


class WebhookCog(TacobotCog):
    # group = app_commands.Group(name="webhook", description="Webhook Handler")

    def __init__(self, bot: TacoBot):
        super().__init__(bot, "webhook")

        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.http_server = None

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener("on_ready")
    async def initialize_server(self):
        _method = inspect.stack()[0][3]
        try:
            settings = self.get_cog_settings()
            if not settings.get("enabled", False):
                # the cog is disabled, so we don't need to start the server
                return

            if self.http_server is None or not await self.http_server.is_running():
                self.http_server = HttpServer()

                self.http_server.set_http_debug_enabled(True)
                self.load_webhook_handlers()

                self.http_server.add_default_response_headers(
                    {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': '*'}
                )

                listen_address = "0.0.0.0"
                listen_port = settings.get("port", 8090)

                await self.http_server.start(listen_address, listen_port)
                self.log.info(
                    0, f"{self._module}.{self._class}.{_method}", f'Webhook Started Listening => :{listen_port}'
                )
                # we dont need to call "serve_forever" because this task is already running in the background

        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    def load_webhook_handlers(self):
        _method = inspect.stack()[0][3]
        try:
            if not os.path.exists("bot/lib/webhook/handlers"):
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "No handlers found")
                return
            if not self.http_server:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "No http server found")
                return

            handlers = [
                f"bot.lib.webhook.handlers.{os.path.splitext(f)[0]}"
                for f in os.listdir("bot/lib/webhook/handlers")
                if f.endswith(".py") and not f.startswith("_") and not f.startswith("BaseWebhookHandler")
            ]

            for handler in handlers:
                try:
                    module_path, class_name = handler.rsplit('.', 1)
                    full_module_path = f"{module_path}.{class_name}"
                    module = import_module(full_module_path)
                    # create an instance of the handler
                    handler_instance = getattr(module, class_name)
                    self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Loading handler {handler}")
                    self.http_server.add_handler(handler_instance(self.bot))
                except Exception as e:
                    self.log.error(
                        0,
                        f"{self._module}.{self._class}.{_method}",
                        f"Failed to load extension {handler}: {e}",
                        traceback.format_exc(),
                    )
        except Exception as e:
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Failed to load handler {handler}: {e}",
                traceback.format_exc(),
            )

    # def get_cog_settings(self, guildId: int = 0) -> dict:
    #     return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    # def get_settings(self, guildId: int, section: str) -> dict:
    #     if not section or section == "":
    #         raise Exception("No section provided")
    #     cog_settings = self.settings.get_settings(guildId, section)
    #     if not cog_settings:
    #         raise Exception(f"No '{section}' settings found for guild {guildId}")
    #     return cog_settings

    # def get_tacos_settings(self, guildId: int = 0) -> dict:
    #     return self.get_settings(guildId=guildId, section="tacos")


async def setup(bot):
    webhook = WebhookCog(bot)
    await bot.add_cog(webhook)
