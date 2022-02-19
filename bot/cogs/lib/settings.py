import sys
import os
import traceback
import glob
import typing
from . import utils
import json
from . import dbprovider

class Settings:
    APP_VERSION = "1.0.0-snapshot"
    BITRATE_DEFAULT = 64

    def __init__(self):
        try:
            with open('app.manifest', encoding="UTF-8") as json_file:
                self.__dict__.update(json.load(json_file))
        except Exception as e:
            print(e, file=sys.stderr)

        self.bot_owner = utils.dict_get(os.environ, 'BOT_OWNER', default_value= '262031734260891648')
        self.log_level = utils.dict_get(os.environ, 'LOG_LEVEL', default_value = 'DEBUG')
        self.language = utils.dict_get(os.environ, "LANGUAGE", default_value = "en-us").lower()
        self.db_url = utils.dict_get(os.environ, "MONGODB_URL", default_value = "mongodb://localhost:27017/tacobot")
        # self.load_language_manifest()
        # self.load_strings()

        dbp = utils.dict_get(os.environ, 'DB_PROVIDER', default_value = 'DEFAULT').upper()
        self.db_provider = dbprovider.DatabaseProvider[dbp]
        if not self.db_provider:
            self.db_provider = dbprovider.DatabaseProvider.DEFAULT

    def get_settings(self, db, guildId: int, name:str):
        return db.get_settings(guildId, name)

    # def load_strings(self):
    #     self.strings = {}

    #     lang_files = glob.glob(os.path.join(os.path.dirname(__file__), "../../../languages", "[a-z][a-z]-[a-z][a-z].json"))
    #     languages = [os.path.basename(f)[:-5] for f in lang_files if os.path.isfile(f)]
    #     for lang in languages:
    #         self.strings[lang] = {}
    #         try:
    #             lang_json = os.path.join("languages", f"{lang}.json")
    #             if not os.path.exists(lang_json) or not os.path.isfile(lang_json):
    #                 # THIS SHOULD NEVER GET HERE
    #                 continue

    #             with open(lang_json, encoding="UTF-8") as lang_file:
    #                 self.strings[lang].update(json.load(lang_file))
    #         except Exception as e:
    #             print(e, file=sys.stderr)
    #             raise e

    # def load_language_manifest(self):
    #     lang_manifest = os.path.join(os.path.dirname(__file__), "../../../languages/manifest.json")
    #     self.languages = {}
    #     if os.path.exists(lang_manifest):
    #         with open(lang_manifest, encoding="UTF-8") as manifest_file:
    #             self.languages.update(json.load(manifest_file))
