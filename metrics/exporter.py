import inspect
import os

from metrics.config import TacoBotMetricsConfig
from bot.cogs.lib.logger import Log
from bot.cogs.lib.loglevel import LogLevel
from bot.cogs.lib.utils import dict_get
from metrics.tacobot import TacoBotMetrics
from prometheus_client import start_http_server


class MetricsExporter:
    def __init__(self):
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        log_level_value = dict_get(os.environ, 'LOG_LEVEL', default_value='DEBUG')

        log_level = LogLevel[log_level_value.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG
        self.log = Log(log_level)

    def run(self):
        _method = inspect.stack()[1][3]
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
