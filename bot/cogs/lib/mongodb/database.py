
import inspect
import os
import sys
import traceback
import typing

from pymongo import MongoClient
from bot.cogs.lib import loglevel, settings, utils
from bot.cogs.lib.mongodb.basedatabase import BaseDatabase
from bot.cogs.lib.colors import Colors

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
