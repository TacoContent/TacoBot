from pymongo import MongoClient
from pymongo.database import Database
from typing import Optional
from .constants import MONGODB_URL
from .logger import logger

class DatabaseConnection:
    _instance: Optional['DatabaseConnection'] = None
    _client: Optional[MongoClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def connect(self):
        if self._client is None:
            try:
                logger.info("Connecting to MongoDB...")
                self._client = MongoClient(MONGODB_URL)
                # Force a connection check
                self._client.admin.command('ping')
                logger.info("Successfully connected to MongoDB.")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                self._client = None
                raise

    def get_database(self, db_name: str = "tacobot") -> Optional[Database]:
        if self._client:
            return self._client[db_name]
        return None

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            logger.info("MongoDB connection closed.")

# Global instance
db_connection = DatabaseConnection()
