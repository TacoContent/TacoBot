import inspect
import os
import traceback
import typing

import requests
from bot.lib import logger
from bot.lib.enums import loglevel
from bot.lib.settings import Settings


class SteamApiClient:
    def __init__(self, settings: Settings):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]

        self.base_url = 'https://store.steampowered.com/api'
        self.settings = settings
        self.headers = {'User-Agent': f'TacoBot/{self.settings.APP_VERSION}'}
        log_level_str = getattr(self.settings, 'log_level', 'DEBUG')
        log_level = (
            loglevel.LogLevel[log_level_str.upper()]
            if log_level_str.upper() in loglevel.LogLevel.__members__
            else loglevel.LogLevel.DEBUG
        )
        self.log = logger.Log(minimumLogLevel=log_level)

    def get_app_id_from_url(self, url: str):
        _method = inspect.stack()[0][3]
        if 'store.steampowered.com' not in url:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", f"Not Steam URL: {url}")
            return None

        # if url ends with / then remove it
        if url[-1] == '/':
            url = url[:-1]
        if 'app' in url:
            # if the url ends with an app id use index -1
            if url.split('/')[-1].isnumeric():
                return url.split('/')[-1]
            # otherwise use index -2
            else:
                app_id = url.split('/')[-2]
                return app_id

        self.log.warn(0, f"{self._module}.{self._class}.{_method}", f"Could not find app id in {url}")
        return None

    def get_app_details(self, app_id: str):
        _method = inspect.stack()[0][3]
        try:
            url = f'{self.base_url}/appdetails?appids={app_id}&cc=us&l=en'
            response = requests.get(url, headers=self.headers)
            result: typing.Any = response.json()
            return result
        except Exception as e:
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Failed to get app details for {app_id}: {e}",
                traceback.format_exc(),
            )
            return None
