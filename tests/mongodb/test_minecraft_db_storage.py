import pytest

from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.models.MinecraftUserStorageEntry import MinecraftUserStorageItem


class FakeCollection:
    def __init__(self):
        # store entries by tuple (guild_id,user_id,uuid)
        self._store = {}

    def _key(self, query):
        return (query.get("guild_id"), query.get("user_id"), query.get("uuid"))

    def find_one(self, query):
        return self._store.get(self._key(query))

    def update_one(self, filter_query, update, upsert=False):
        key = self._key(filter_query)
        current = self._store.get(key, {})

        # handle $set
        if "$set" in update:
            for path, value in update["$set"].items():
                # support nested storage.item_id or storage.item_id.quantity
                if path.startswith("storage."):
                    parts = path.split(".")
                    # path == storage.<item_id> or storage.<item_id>.quantity
                    if len(parts) == 2:
                        # replace whole item value
                        item_id = parts[1]
                        storage = current.get("storage", {})
                        # value is expected to be a dict
                        storage[item_id] = value
                        current["storage"] = storage
                    elif len(parts) == 3:
                        item_id = parts[1]
                        field = parts[2]
                        storage = current.get("storage", {})
                        item = storage.get(item_id, {})
                        item[field] = value
                        storage[item_id] = item
                        current["storage"] = storage
                else:
                    current[path] = value

        # handle $unset
        if "$unset" in update:
            for path in update["$unset"].keys():
                if path.startswith("storage."):
                    _, item_id = path.split(".", 1)
                    storage = current.get("storage", {})
                    storage.pop(item_id, None)
                    current["storage"] = storage
                else:
                    current.pop(path, None)

        # write back
        if current or upsert:
            self._store[key] = current

    def insert_one(self, document):
        # For logs only - just store under a reserved key
        self._store.setdefault('_inserts', []).append(document)
        return True


class FakeConnection:
    def __init__(self):
        self.minecraft_user_storage = FakeCollection()
        self.minecraft_users = FakeCollection()
        self.logs = FakeCollection()


@pytest.fixture
def db():
    mdb = MinecraftDatabase()
    # inject fake connection and a truthy client so open() is not required
    mdb.connection = FakeConnection()
    mdb.client = True
    return mdb


def test_get_user_storage_not_found(db):
    res = db.get_user_storage(1, 2, "uuid-x")
    assert res is None


def test_get_user_storage_returns_entry(db):
    col = db.connection.minecraft_user_storage
    key = ("1", "2", "uuid-x")
    col._store[key] = {
        "user_id": "2",
        "guild_id": "1",
        "uuid": "uuid-x",
        "username": "Player",
        "storage": {"minecraft:diamond": {"item_id": "minecraft:diamond", "quantity": 10, "metadata": {"name": "Diamond"}}},
    }

    entry = db.get_user_storage(1, 2, "uuid-x")
    assert entry is not None
    assert entry.user_id == "2"
    assert "minecraft:diamond" in entry.storage
    diamond = entry.storage["minecraft:diamond"]
    assert diamond.item_id == "minecraft:diamond"
    assert diamond.quantity == 10


def test_withdraw_user_storage_missing_or_not_enough(db):
    # empty db -> missing (use a variant id key)
    assert db.withdraw_user_storage(1, 2, "uuid-x", "stick-variant", 1) == (None, False)

    # add entry with item quantity 1, withdraw 2 -> not enough
    col = db.connection.minecraft_user_storage
    key = ("1", "2", "uuid-x")
    col._store[key] = {
        "user_id": "2",
        "guild_id": "1",
        "uuid": "uuid-x",
        "username": "Test",
        "storage": {"stick-variant": {"item_id": "minecraft:stick", "variant_id": "stick-variant", "quantity": 1, "metadata": {}}},
    }

    # supply the correct variant id when withdrawing
    assert db.withdraw_user_storage(1, 2, "uuid-x", "stick-variant", 2) == (None, False)


def test_withdraw_user_storage_decrement_and_remove(db):
    col = db.connection.minecraft_user_storage
    key = ("1", "2", "uuid-dep")
    # start with quantity 5
    col._store[key] = {
        "user_id": "2",
        "guild_id": "1",
        "uuid": "uuid-dep",
        "username": "DepositTest",
        "storage": {"egg-variant": {"item_id": "minecraft:egg", "variant_id": "egg-variant", "quantity": 5, "metadata": {}}},
    }

    # withdraw 3 -> quantity becomes 2
    # withdraw using the variant id key
    withdrawn_item, ok = db.withdraw_user_storage(1, 2, "uuid-dep", "egg-variant", 3)
    assert ok is True
    stored = col._store[key]
    assert stored["storage"]["egg-variant"]["quantity"] == 2

    # withdraw remaining 2 -> should remove item
    withdrawn_item2, ok2 = db.withdraw_user_storage(1, 2, "uuid-dep", "egg-variant", 2)
    assert ok2 is True
    stored2 = col._store[key]
    assert "egg-variant" not in stored2.get("storage", {})


def test_deposit_user_storage_new_and_existing(db):
    col = db.connection.minecraft_user_storage
    key = ("10", "20", "uuid-dp")

    # Create a match for minecraft user record so deposit can validate user exists
    db.connection.minecraft_users._store[("10", "20", None)] = {"user_id": "20", "guild_id": "10", "uuid": "uuid-dp", "username": "TestUser"}

    # deposit into new user -> should add upsert
    item = MinecraftUserStorageItem(item_id="minecraft:pearl", variant_id="pearl-variant", quantity=4, metadata={"note": "test"})
    ok = db.deposit_user_storage(10, 20, "uuid-dp", item)
    assert ok is True

    stored = col._store[key]
    assert "pearl-variant" in stored["storage"]
    assert stored["storage"]["pearl-variant"]["quantity"] == 4

    # deposit additional quantity to existing item -> should increment
    item2 = MinecraftUserStorageItem(item_id="minecraft:pearl", variant_id="pearl-variant", quantity=6, metadata={})
    ok2 = db.deposit_user_storage(10, 20, "uuid-dp", item2)
    assert ok2 is True

    stored2 = col._store[key]
    assert stored2["storage"]["pearl-variant"]["quantity"] == 10
