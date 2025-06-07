import os
import threading
import typing

from bot.lib import utils
from pymongo import MongoClient


class MongoClientSingleton:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_client(cls, db_url: typing.Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    if db_url is None:
                        # If no db_url is provided, use the environment variable or default value
                        db_url = utils.dict_get(
                            os.environ, "MONGODB_URL", default_value=f"mongodb://localhost:27017/tacobot"
                        )
                    cls._instance = MongoClient(db_url)
        return cls._instance

    @classmethod
    def close_client(cls):
        if cls._instance is not None:
            with cls._lock:
                if cls._instance is not None:
                    cls._instance.close()
                    cls._instance = None
