import inspect
import os
import traceback

import requests

from bot.lib import logger, settings
from bot.lib.enums import loglevel


class SteamApiClient:
    def __init__(self):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        # self.api_key = os.environ.get('STEAM_API_KEY')
        self.base_url = 'https://store.steampowered.com/api'
        self.settings = settings.Settings()
        self.headers = {'User-Agent': f'TacoBot/{self.settings.APP_VERSION}'}
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

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
            result = response.json()
            return result
        except Exception as e:
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Failed to get app details for {app_id}: {e}",
                traceback.format_exc(),
            )
            return None
