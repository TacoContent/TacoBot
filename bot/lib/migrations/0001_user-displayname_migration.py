import inspect
import os
import traceback

from bot.lib.mongodb.migration_base import MigrationBase


class Migration(MigrationBase):
    def __init__(self) -> None:
        super().__init__()
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self._version = 0

    def run(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            self.log.info(0, f"{self._module}.{self._class}.{_method}", "Starting migration")

            users_collection = self.connection.users  # type: ignore
            users_cursor = users_collection.find({})

            for user_doc in users_cursor:
                updated_fields = {}
                if "display_name" not in user_doc and "displayname" in user_doc:
                    updated_fields["display_name"] = user_doc["displayname"]

                elif "displayname" not in user_doc and "display_name" in user_doc:
                    updated_fields["displayname"] = user_doc["display_name"]

                if updated_fields:
                    users_collection.update_one(
                        {"_id": user_doc["_id"]},
                        {"$set": updated_fields}
                    )
                    self.log.info(0, f"{self._module}.{self._class}.{_method}", f"Updated user {user_doc['_id']} with fields: {updated_fields}")

            self.track_run(True)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"Error during migration: {str(e)}")
            traceback.print_exc()
        # if the display_name field does not exist, but displayname does, copy it over
