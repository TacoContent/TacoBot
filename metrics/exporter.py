import inspect
import os
import traceback

from metrics.config import TacoBotMetricsConfig
from bot.cogs.lib.logger import Log
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.settings import Settings
from bot.cogs.lib.utils import dict_get
from metrics.tacobot import TacoBotMetrics
from prometheus_client import start_http_server


class MetricsExporter:
    def __init__(self):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.settings = Settings()
        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG
        self.log = Log(log_level)

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Exporter initialized")

    def run(self):
        _method = inspect.stack()[1][3]
        try:
            config_file = dict_get(os.environ, "TBE_CONFIG_FILE", default_value="./config/.configuration.yaml")
            config = TacoBotMetricsConfig(config_file)
            app_metrics = TacoBotMetrics(config)
            self.log.info(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Exporter Starting Listen => :{config.metrics['port']}/metrics",
            )
            start_http_server(config.metrics["port"])
            app_metrics.run_metrics_loop()
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
