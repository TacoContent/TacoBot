import codecs
import os

import yaml
from bot.lib.utils import dict_get


class TacoBotMetricsConfig:
    def __init__(self, file: str):
        # set defaults for config from environment variables if they exist
        self.metrics = {
            "port": int(dict_get(os.environ, "TBE_CONFIG_METRICS_PORT", "8932")),
            "pollingInterval": int(dict_get(os.environ, "TBE_CONFIG_METRICS_POLLING_INTERVAL", "30")),
        }

        try:
            # check if file exists
            if os.path.exists(file):
                with codecs.open(file, encoding="utf-8-sig", mode="r") as f:
                    settings = yaml.safe_load(f)
                    self.__dict__.update(settings)
        except yaml.YAMLError as exc:
            raise exc
