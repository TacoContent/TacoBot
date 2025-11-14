import inspect
import os
import traceback

from bot.lib.enums.loglevel import LogLevel
from bot.lib.logger import Log
from bot.lib.mongodb.metrics import MetricsDatabase
from bot.lib.settings import Settings
from bot.lib.utils import dict_get
from metrics.config import TacoBotMetricsConfig
from metrics.tacobot import TacoBotMetrics
from prometheus_client import start_http_server


class MetricsExporter:
    def __init__(self, settings: Settings):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings

        log_level = LogLevel.DEBUG
        try:
            log_level = LogLevel[self.settings.log_level.upper()]
            self.log = Log(log_level)
        except Exception as ex:
            self.log = Log(log_level)
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Exporter initialized")

    def run(self):
        _method = inspect.stack()[1][3]
        try:
            metrics_db = MetricsDatabase()
            config_file = dict_get(os.environ, "TBE_CONFIG_FILE", default_value="./config/.configuration.yaml")
            config = TacoBotMetricsConfig(config_file)
            app_metrics = TacoBotMetrics(config, metrics_db, self.settings)
            self.log.info(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Exporter Starting Listen => :{config.metrics['port']}/metrics",
            )
            start_http_server(config.metrics["port"])
            app_metrics.run_metrics_loop()
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
