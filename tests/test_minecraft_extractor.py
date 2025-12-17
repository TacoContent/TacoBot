import sys
import importlib
import json
import base64
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.fixture(autouse=True)
def add_minecraft_path(monkeypatch, tmp_path):
    # Ensure the scripts/minecraft directory is on sys.path so we can import modules
    repo_root = Path(__file__).resolve().parents[1]
    minecraft_dir = repo_root / "scripts" / "minecraft"
    sys.path.insert(0, str(minecraft_dir))
    yield
    # cleanup
    try:
        sys.path.remove(str(minecraft_dir))
    except Exception:
        pass


def write_jar(jar_path: Path, files: dict):
    with ZipFile(jar_path, "w") as z:
        for path, content in files.items():
            z.writestr(path, content)


def load_items_json(metadata_file: Path):
    if not metadata_file.exists():
        return []
    return json.loads(metadata_file.read_text(encoding="utf-8"))


# Simple fake DB helpers used by MongoDB-related tests
class FakeCollection:
    def __init__(self, existing_ids=None):
        self.inserted = []
        self._existing = existing_ids or []

    def insert_one(self, doc):
        self.inserted.append(doc)

    def distinct(self, key):
        if key == "id":
            return list(self._existing)
        return []


class FakeDB:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = FakeCollection()
        return self.collections[name]


class FakeConn:
    def __init__(self, db=None):
        self._db = db or FakeDB()
        self.connected = False

    def connect(self):
        self.connected = True

    def get_database(self, db_name="tacobot"):
        return self._db

    def close(self):
        self.connected = False


def test_only_items_with_models_are_extracted(tmp_path, monkeypatch):
    # Arrange: create a temporary jars and output dirs
    jars_dir = tmp_path / "jars"
    assets_dir = tmp_path / "output" / "assets"
    output_dir = tmp_path / "output"
    jars_dir.mkdir()
    assets_dir.mkdir(parents=True)

    jar_file = jars_dir / "test.jar"

    # Create files: new format (items/) for vanilla
    files = {
        "assets/minecraft/textures/item/crafting_table_top.png": b"toppng",
        "assets/minecraft/textures/item/crafting_table.png": b"tablepng",
        "assets/minecraft/items/crafting_table.json": b'{"model": {"type": "minecraft:model", "model": "minecraft:item/crafting_table"}}',
        # no items/crafting_table_top.json -> should be skipped
        "assets/minecraft/lang/en_us.json": json.dumps({"item.minecraft.crafting_table": "Crafting Table"}),
    }
    write_jar(jar_file, files)

    # Monkeypatch constants before importing modules so they use our temp dirs
    import modules.constants as constants

    monkeypatch.setattr(constants, "JARS_DIR", jars_dir)
    monkeypatch.setattr(constants, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(constants, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(constants, "METADATA_FILE", output_dir / "items.json")

    # Reload dependent modules so they pick up the patched constants
    importlib.reload(importlib.import_module("modules.metadata_handler"))
    importlib.reload(importlib.import_module("modules.asset_extractor"))
    importlib.reload(importlib.import_module("modules.db"))
    importlib.reload(importlib.import_module("modules.jar_scanner"))
    from modules.jar_scanner import JarScanner

    # Act
    scanner = JarScanner()
    scanner.process_jar(jar_file)
    scanner.metadata_handler.save_metadata()

    # Assert
    items = load_items_json(constants.METADATA_FILE)
    assert any(item["id"] == "minecraft:crafting_table" for item in items)
    assert not any(item["id"] == "minecraft:crafting_table_top" for item in items)

    # Check that the asset file exists for crafting_table
    assert (assets_dir / "minecraft_crafting_table.png").exists()


def test_old_format_models_are_extracted(tmp_path, monkeypatch):
    """Test that old format (models/item/) from mods are extracted."""
    jars_dir = tmp_path / "jars"
    assets_dir = tmp_path / "output" / "assets"
    output_dir = tmp_path / "output"
    jars_dir.mkdir()
    assets_dir.mkdir(parents=True)

    jar_file = jars_dir / "test_mod.jar"

    img_data = b"MODPNG"
    files = {
        "assets/testmod/models/item/test_item.json": json.dumps({
            "parent": "item/generated",
            "textures": {"layer0": "testmod:item/test_item"}
        }),
        "assets/testmod/textures/item/test_item.png": img_data,
        "assets/testmod/lang/en_us.json": json.dumps({"item.testmod.test_item": "Test Item"}),
    }
    write_jar(jar_file, files)

    import modules.constants as constants
    monkeypatch.setattr(constants, "JARS_DIR", jars_dir)
    monkeypatch.setattr(constants, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(constants, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(constants, "METADATA_FILE", output_dir / "items.json")

    importlib.reload(importlib.import_module("modules.metadata_handler"))
    importlib.reload(importlib.import_module("modules.asset_extractor"))
    importlib.reload(importlib.import_module("modules.db"))
    importlib.reload(importlib.import_module("modules.jar_scanner"))
    from modules.jar_scanner import JarScanner

    scanner = JarScanner()
    scanner.process_jar(jar_file)
    scanner.metadata_handler.save_metadata()

    items = load_items_json(constants.METADATA_FILE)
    assert len(items) == 1
    assert items[0]["id"] == "testmod:test_item"
    assert items[0]["name"] == "Test Item"
    assert (assets_dir / "testmod_test_item.png").exists()


def test_include_asset_adds_base64(tmp_path, monkeypatch):
    jars_dir = tmp_path / "jars"
    assets_dir = tmp_path / "output" / "assets"
    output_dir = tmp_path / "output"
    jars_dir.mkdir()
    assets_dir.mkdir(parents=True)

    jar_file = jars_dir / "test2.jar"

    img_data = b"\x89PNG\r\n\x1a\nPNGDATA"
    files = {
        "assets/minecraft/textures/item/example_item.png": img_data,
        "assets/minecraft/models/item/example_item.json": b"{}",
        "assets/minecraft/lang/en_us.json": json.dumps({"item.minecraft.example_item": "Example Item"}),
    }
    write_jar(jar_file, files)

    import modules.constants as constants
    monkeypatch.setattr(constants, "JARS_DIR", jars_dir)
    monkeypatch.setattr(constants, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(constants, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(constants, "METADATA_FILE", output_dir / "items.json")

    importlib.reload(importlib.import_module("modules.metadata_handler"))
    importlib.reload(importlib.import_module("modules.asset_extractor"))
    importlib.reload(importlib.import_module("modules.db"))
    importlib.reload(importlib.import_module("modules.jar_scanner"))
    from modules.jar_scanner import JarScanner

    scanner = JarScanner(include_asset=True)
    scanner.process_jar(jar_file)
    scanner.metadata_handler.save_metadata()

    items = load_items_json(constants.METADATA_FILE)
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "minecraft:example_item"
    assert "asset_b64" in item
    assert item["asset_b64"] == base64.b64encode(img_data).decode("ascii")


def test_skip_when_asset_file_exists(tmp_path, monkeypatch):
    jars_dir = tmp_path / "jars"
    assets_dir = tmp_path / "output" / "assets"
    output_dir = tmp_path / "output"
    jars_dir.mkdir()
    assets_dir.mkdir(parents=True)

    # Pre-create an asset file to simulate duplicate
    preexisting = assets_dir / "minecraft_dup_item.png"
    preexisting.write_bytes(b"existing")

    jar_file = jars_dir / "test3.jar"
    files = {
        "assets/minecraft/textures/item/dup_item.png": b"DATA",
        "assets/minecraft/models/item/dup_item.json": b"{}",
        "assets/minecraft/lang/en_us.json": json.dumps({"item.minecraft.dup_item": "Dup Item"}),
    }
    write_jar(jar_file, files)

    import modules.constants as constants
    monkeypatch.setattr(constants, "JARS_DIR", jars_dir)
    monkeypatch.setattr(constants, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(constants, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(constants, "METADATA_FILE", output_dir / "items.json")

    importlib.reload(importlib.import_module("modules.metadata_handler"))
    importlib.reload(importlib.import_module("modules.asset_extractor"))
    importlib.reload(importlib.import_module("modules.db"))
    importlib.reload(importlib.import_module("modules.jar_scanner"))
    from modules.jar_scanner import JarScanner

    scanner = JarScanner()
    scanner.process_jar(jar_file)
    scanner.metadata_handler.save_metadata()

    items = load_items_json(constants.METADATA_FILE)
    # No items should be added because asset file already existed
    assert len(items) == 0


def test_mongodb_insertion_with_mock(tmp_path, monkeypatch):
    jars_dir = tmp_path / "jars"
    assets_dir = tmp_path / "output" / "assets"
    output_dir = tmp_path / "output"
    jars_dir.mkdir()
    assets_dir.mkdir(parents=True)

    jar_file = jars_dir / "mongo_test.jar"

    img_data = b"PNGDATA"
    files = {
        "assets/minecraft/textures/item/mongo_item.png": img_data,
        "assets/minecraft/models/item/mongo_item.json": b"{}",
        "assets/minecraft/lang/en_us.json": json.dumps({"item.minecraft.mongo_item": "Mongo Item"}),
    }
    write_jar(jar_file, files)

    import modules.constants as constants
    monkeypatch.setattr(constants, "JARS_DIR", jars_dir)
    monkeypatch.setattr(constants, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(constants, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(constants, "METADATA_FILE", output_dir / "items.json")

    # Create a fake DB connection and collection to capture inserted docs
    class FakeCollection:
        def __init__(self, existing_ids=None):
            self.inserted = []
            self._existing = existing_ids or []

        def insert_one(self, doc):
            self.inserted.append(doc)

        def distinct(self, key):
            if key == "id":
                return list(self._existing)
            return []

    class FakeDB:
        def __init__(self):
            self.collections = {}

        def __getitem__(self, name):
            if name not in self.collections:
                self.collections[name] = FakeCollection()
            return self.collections[name]

    class FakeConn:
        def __init__(self):
            self._db = FakeDB()
            self.connected = False

        def connect(self):
            self.connected = True

        def get_database(self, db_name="tacobot"):
            return self._db

        def close(self):
            self.connected = False

    fake_conn = FakeConn()

    # Reload modules and inject fake connection into metadata handler
    importlib.reload(importlib.import_module("modules.metadata_handler"))
    importlib.reload(importlib.import_module("modules.asset_extractor"))
    importlib.reload(importlib.import_module("modules.db"))
    import modules.metadata_handler as mh
    mh.db_connection = fake_conn

    importlib.reload(importlib.import_module("modules.jar_scanner"))
    from modules.jar_scanner import JarScanner

    scanner = JarScanner(use_mongodb=True, collection_name="test_collection", include_asset=True)
    scanner.process_jar(jar_file)
    scanner.metadata_handler.save_metadata()

    # Assert that the fake collection got an inserted document
    fake_collection = fake_conn.get_database()["test_collection"]
    assert len(fake_collection.inserted) == 1
    inserted = fake_collection.inserted[0]
    assert inserted["id"] == "minecraft:mongo_item"
    assert "asset_b64" in inserted


def test_mongodb_skips_existing_item_from_db(tmp_path, monkeypatch):
    jars_dir = tmp_path / "jars"
    assets_dir = tmp_path / "output" / "assets"
    output_dir = tmp_path / "output"
    jars_dir.mkdir()
    assets_dir.mkdir(parents=True)

    jar_file = jars_dir / "mongo_test2.jar"
    files = {
        "assets/minecraft/textures/item/already_item.png": b"DATA",
        "assets/minecraft/models/item/already_item.json": b"{}",
        "assets/minecraft/lang/en_us.json": json.dumps({"item.minecraft.already_item": "Already Item"}),
    }
    write_jar(jar_file, files)

    import modules.constants as constants
    monkeypatch.setattr(constants, "JARS_DIR", jars_dir)
    monkeypatch.setattr(constants, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(constants, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(constants, "METADATA_FILE", output_dir / "items.json")

    # Fake connection with an existing id
    class FakeCollection2(FakeCollection):
        def __init__(self):
            super().__init__(existing_ids=["minecraft:already_item"])

    class FakeDB2:
        def __init__(self):
            self.collections = {"test_collection2": FakeCollection2()}

        def __getitem__(self, name):
            return self.collections[name]

    class FakeConn2:
        def __init__(self):
            self._db = FakeDB2()

        def connect(self):
            pass

        def get_database(self, db_name="tacobot"):
            return self._db

        def close(self):
            pass

    fake_conn2 = FakeConn2()

    importlib.reload(importlib.import_module("modules.metadata_handler"))
    importlib.reload(importlib.import_module("modules.asset_extractor"))
    importlib.reload(importlib.import_module("modules.db"))
    import modules.metadata_handler as mh2
    mh2.db_connection = fake_conn2

    importlib.reload(importlib.import_module("modules.jar_scanner"))
    from modules.jar_scanner import JarScanner

    scanner = JarScanner(use_mongodb=True, collection_name="test_collection2")
    scanner.process_jar(jar_file)
    scanner.metadata_handler.save_metadata()

    # The fake collection should have no new inserts because the id already existed
    fake_collection2 = fake_conn2.get_database()["test_collection2"]
    assert len(fake_collection2.inserted) == 0


def test_model_variants_are_excluded(tmp_path, monkeypatch):
    """Test that model variants (trim, pulling, etc.) are filtered out."""
    jars_dir = tmp_path / "jars"
    assets_dir = tmp_path / "output" / "assets"
    output_dir = tmp_path / "output"
    jars_dir.mkdir()
    assets_dir.mkdir(parents=True)

    jar_file = jars_dir / "test_variants.jar"

    files = {
        # Base item (should be extracted)
        "assets/minecraft/models/item/diamond_chestplate.json": json.dumps({
            "parent": "item/generated",
            "textures": {"layer0": "minecraft:item/diamond_chestplate"}
        }),
        "assets/minecraft/textures/item/diamond_chestplate.png": b"CHESTPLATE",
        
        # Trim variant (should be skipped)
        "assets/minecraft/models/item/diamond_chestplate_amethyst_trim.json": json.dumps({
            "parent": "item/generated",
            "textures": {"layer0": "minecraft:item/diamond_chestplate"}
        }),
        
        # Bow base (should be extracted)
        "assets/minecraft/models/item/bow.json": json.dumps({
            "parent": "item/generated",
            "textures": {"layer0": "minecraft:item/bow"}
        }),
        "assets/minecraft/textures/item/bow.png": b"BOW",
        
        # Bow pulling variant (should be skipped)
        "assets/minecraft/models/item/bow_pulling_0.json": json.dumps({
            "parent": "item/generated",
            "textures": {"layer0": "minecraft:item/bow_pulling_0"}
        }),
        
        "assets/minecraft/lang/en_us.json": json.dumps({
            "item.minecraft.diamond_chestplate": "Diamond Chestplate",
            "item.minecraft.bow": "Bow"
        }),
    }
    write_jar(jar_file, files)

    import modules.constants as constants
    monkeypatch.setattr(constants, "JARS_DIR", jars_dir)
    monkeypatch.setattr(constants, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(constants, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(constants, "METADATA_FILE", output_dir / "items.json")

    importlib.reload(importlib.import_module("modules.metadata_handler"))
    importlib.reload(importlib.import_module("modules.asset_extractor"))
    importlib.reload(importlib.import_module("modules.db"))
    importlib.reload(importlib.import_module("modules.jar_scanner"))
    from modules.jar_scanner import JarScanner

    scanner = JarScanner()
    scanner.process_jar(jar_file)
    scanner.metadata_handler.save_metadata()

    items = load_items_json(constants.METADATA_FILE)
    item_ids = [i["id"] for i in items]
    
    # Base items should be present
    assert "minecraft:diamond_chestplate" in item_ids
    assert "minecraft:bow" in item_ids
    
    # Variants should be excluded
    assert "minecraft:diamond_chestplate_amethyst_trim" not in item_ids
    assert "minecraft:bow_pulling_0" not in item_ids
    
    # Should only have 2 items (the base items)
    assert len(items) == 2
