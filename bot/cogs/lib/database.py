
from traceback import print_exc

class Database():

    def __init__(self):
        pass
    def open(self):
        pass
    def close(self):
        pass

    def insert_log(self, guildId: int, level: str, method: str, message: str, stack: str = None):
        pass
    def clear_log(self, guildId: int):
        pass

    def UPDATE_SCHEMA(self):
        pass
