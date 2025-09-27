import os

from bot.lib import settings
from bot.lib.mongodb.basedatabase import BaseDatabase


class Database(BaseDatabase):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = settings.Settings()
        self.client = None
        self.connection = None
        self.db_url = self.settings.db_url
        pass


