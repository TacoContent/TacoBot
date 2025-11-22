import inspect
import os
import traceback
from importlib import import_module

from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.helpers import MessageHelper
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from discord.ext import commands
from httpserver import HttpServer


class HttpHandlerCog(TacobotCog):
    # group = app_commands.Group(name="webhook", description="Webhook Handler")

    def __init__(
        self, bot: TacoBot, tracking_db: TrackingDatabase, message_helper: MessageHelper, settings: Settings
    ) -> None:
        super().__init__(bot, "webhook", settings=settings)

        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.http_server = None

        self.message_helper = message_helper
        self.tracking_db = tracking_db

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener("on_ready")
    async def initialize_server(self):
        _method = inspect.stack()[0][3]
        try:
            await self._initialize_server()

        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    async def _initialize_server(self):
        _method = inspect.stack()[0][3]
        settings = self.get_cog_settings()
        if not settings.get("enabled", False):
            # the cog is disabled, so we don't need to start the server
            return

        if self.http_server is None or not await self.http_server.is_running():
            self.http_server = HttpServer()

            self.http_server.set_http_debug_enabled(True)
            # self.load_webhook_handlers()
            # self.recursive_load_handlers("bot/lib/http/handlers/api")
            # self.recursive_load_handlers("bot/lib/http/handlers/webhook")
            self.recursive_load_handlers("bot/lib/http/handlers")

            self.http_server.add_default_response_headers(
                {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': '*'}
            )

            listen_address = "0.0.0.0"
            listen_port = settings.get("port", 8090)

            await self.http_server.start(listen_address, listen_port)
            self.log.info(0, f"{self._module}.{self._class}.{_method}", f'Webhook Started Listening => :{listen_port}')
            # we dont need to call "serve_forever" because this task is already running in the background

    def load_webhook_handlers(self):
        _method = inspect.stack()[0][3]
        try:
            if not os.path.exists("bot/lib/http/handlers"):
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "No handlers found")
                return
            if not self.http_server:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "No http server found")
                return

            handlers = [
                f"bot.lib.http.handlers.{os.path.splitext(f)[0]}"
                for f in os.listdir("bot/lib/http/handlers")
                if f.endswith(".py")
                and not f.startswith("_")
                and not f.startswith("ApiHttpHandler")
                and not f.startswith("BaseWebhookHandler")
                and not f.startswith("BaseHttpHandler")
            ]

            for handler in handlers:
                try:
                    module_path, class_name = handler.rsplit('.', 1)
                    full_module_path = f"{module_path}.{class_name}"
                    module = import_module(full_module_path)
                    # create an instance of the handler
                    # handler_instance = getattr(module, class_name)
                    handler_instance = getattr(module, "setup", None)
                    if handler_instance is None or not callable(handler_instance):
                        self.log.error(
                            0,
                            f"{self._module}.{self._class}.{_method}",
                            f"No setup function found in {full_module_path}",
                        )
                        continue
                    self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Loading handler {handler}")
                    handler_instance(bot=self.bot, http_server=self.http_server)
                    # self.http_server.add_handler(handler_instance(self.bot))
                except Exception as e:
                    self.log.error(
                        0,
                        f"{self._module}.{self._class}.{_method}",
                        f"Failed to load extension {handler}: {e}",
                        traceback.format_exc(),
                    )
        except Exception as e:
            self.log.error(
                0, f"{self._module}.{self._class}.{_method}", f"Failed to load handlers: {e}", traceback.format_exc()
            )

    def recursive_load_handlers(self, path: str):
        _method = inspect.stack()[0][3]
        try:
            if not self.http_server:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", "No http server found")
                return

            for root, dirs, files in os.walk(path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if (
                        file.endswith(".py")
                        and not file.startswith("_")
                        and not file.startswith("__")
                        and not file.endswith(".pyc")
                        and not file.startswith("Base")
                        and not file.startswith("ApiHttpHandler")
                        and file.endswith("Handler.py")
                    ):
                        self.log.info(0, f"{self._module}.{self._class}.{_method}", f"Found file: {full_path}")
                        # convert the file path to a module path by replacing the path separator with a dot
                        # and removing the file extension
                        mod_path, class_name = (
                            full_path.replace(os.sep, ".")
                            .replace('/', '.')
                            .replace('\\', '.')
                            .replace(".py", "")
                            .rsplit('.', 1)
                        )
                        full_module_path = f"{mod_path}.{class_name}"
                        module = import_module(full_module_path)

                        # handler_instance = getattr(module, class_name)
                        # call setup from the module if it exists
                        handler_instance = getattr(module, "setup", None)
                        if handler_instance is None or not callable(handler_instance):
                            self.log.error(
                                0,
                                f"{self._module}.{self._class}.{_method}",
                                f"No setup function found in {full_module_path}",
                            )
                            continue
                        self.log.debug(
                            0, f"{self._module}.{self._class}.{_method}", f"Loading handler {full_module_path}"
                        )
                        # self.http_server.add_handler(handler_instance(self.bot))
                        handler_instance(bot=self.bot, http_server=self.http_server)

                for dir in dirs:
                    self.recursive_load_handlers(dir)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())


async def setup(bot):
    settings = Settings()
    tracking_db = TrackingDatabase()
    message_helper = MessageHelper(bot, settings)
    handler = HttpHandlerCog(bot, settings=settings, tracking_db=tracking_db, message_helper=message_helper)
    await bot.add_cog(handler)
