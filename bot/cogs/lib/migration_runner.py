import traceback
import os
from .migration_base import MigrationBase

class MigrationRunner():
    def __init__(self) -> None:
        self._module = os.path.basename(__file__)[:-3]

        # get migrations from migrations folder
        self._migrations = []
        for file in os.listdir(os.path.join(os.getcwd(), "bot", "cogs", "lib", "migrations")):
            if file.endswith("_migration.py"):
                print(f"Found migration {file[:-3]}")
                self._migrations.append({
                    "id": int(file[:-3].split("_")[0]),
                    "name": file[:-3]
                })

        # sort migrations by id
        self._migrations.sort(key=lambda x: x["id"])

        # load migrations and run them if they haven't been run yet
    def start_migrations(self) -> None:
        for migration in self._migrations:
            try:
                module = __import__(f"bot.cogs.lib.migrations.{migration['name']}", fromlist=["Migration"])
                migration_class = getattr(module, "Migration")
                migration_instance = migration_class()
                if migration_instance.needs_run():
                    print(f"Running migration {migration}")
                    migration_instance.run()
                else:
                    print(f"Migration {migration} has already been run")
            except Exception as ex:
                print(ex)
                traceback.print_exc()
                break
