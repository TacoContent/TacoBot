import discord
import discordhealthcheck

from .cogs.lib import logger
from .cogs.lib import loglevel
from .cogs.lib import dbprovider
from .cogs.lib import settings

class TacoBotClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = settings.Settings()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)

    # 2.0 upgrade...
    async def startup_hook(self):
        # super().run(token, reconnect=reconnect, log_handler=log_handler, log_formatter=log_formatter, log_level=log_level, root_logger=root_logger)
        self.log.debug(0, "TacoBotClient.setup_hook", "Setting up bot")
        self.log.debug(0, "TacoBotClient.setup_hook", "Starting Healthcheck Server")
        self.healthcheck_server = await discordhealthcheck.start(self)
        # Later you can close or check on self.healthcheck_server
