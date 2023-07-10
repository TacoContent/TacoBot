import traceback
import os
from ..migration_base import MigrationBase

class Migration(MigrationBase):
    def __init__(self) -> None:
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._version = 0

    def run(self) -> None:
        try:
            if self.connection is None:
                self.open()

            # update all game keys that don't have a cost to 500

            result = self.connection.game_keys.update_many(
                {
                    "cost": {
                        "$exists": False
                    }
                },
                {
                    "$set": {
                        "cost": 500
                    }
                }
            )

            print(f"Updated {result.modified_count} game keys with no cost to cost of 500")


            self.track_run(True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            self.track_run(False)
        finally:
            if self.connection is not None:
                self.close()
