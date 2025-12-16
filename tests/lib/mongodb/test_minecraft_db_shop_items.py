import types

from bot.lib.models.MinecraftShopEntry import MinecraftShopEntry
from bot.lib.models.MinecraftShopItem import MinecraftShopItem
from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry
from bot.lib.mongodb.minecraft import MinecraftDatabase


class FakeColl:
    def __init__(self, find_iter=None, should_raise=False):
        self.find_iter = find_iter or []
        self.should_raise = should_raise

    def find(self, q):
        if self.should_raise:
            raise RuntimeError('boom')
        for d in self.find_iter:
            yield d


def make_open_stub(db, mapping):
    def _open():
        db.client = object()
        db.connection = types.SimpleNamespace(**mapping)

    return _open


def test_get_shop_items_filters_by_sell_and_buy_and_admin(monkeypatch):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"

    docs = [
        {
            'guild_id': '1',
            'user_id': None,
            'enabled': True,
            'shop_id': 's1',
            'shop': {
                'v1': {'item_id': 'minecraft:apple', 'variant_id': 'v1', 'buy': 0, 'sell': 5, 'enabled': True},
                'v2': {'item_id': 'minecraft:stone', 'variant_id': 'v2', 'buy': 10, 'sell': 0, 'enabled': True},
                'v3': {'item_id': 'minecraft:disabled', 'variant_id': 'v3', 'buy': 0, 'sell': 0, 'enabled': False},
            },
        }
    ]

    fake = FakeColl(find_iter=docs)
    db.client = object()
    db.connection = types.SimpleNamespace(minecraft_shops=fake)
    db.settings.primary_guild_id = 1

    # sell action should include only items with sell > 0 and enabled True
    res_sell = db.get_shop_items(guild_id=1, action='sell', admin_list=False)
    assert isinstance(res_sell, list)
    assert len(res_sell) == 1
    shop_entry: MinecraftShopEntry = res_sell[0]
    assert 'v1' in shop_entry.shop and 'v2' not in shop_entry.shop and 'v3' not in shop_entry.shop

    # buy action should include items with buy > 0
    res_buy = db.get_shop_items(guild_id=1, action='buy', admin_list=False)
    assert 'v2' in res_buy[0].shop and 'v1' not in res_buy[0].shop

    # admin_list True should include items irrespective of buy/sell numbers, but still respects the enabled flag
    res_admin = db.get_shop_items(guild_id=1, admin_list=True)
    assert 'v1' in res_admin[0].shop and 'v2' in res_admin[0].shop and 'v3' not in res_admin[0].shop


def test_get_shop_items_with_exceptions_returns_empty(capsys):
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"
    fake = FakeColl(should_raise=True)
    db.client = object()
    db.connection = types.SimpleNamespace(minecraft_shops=fake)

    res = db.get_shop_items(guild_id=1)
    assert res == []
    out = capsys.readouterr()
    assert 'ERROR' in out.out or 'ERROR' in out.err


def test_has_op_level_true_false_and_missing_user():
    db = MinecraftDatabase()
    db.db_url = "mongodb://ok"
    # user has op enabled level 3; simulate mc_user object with op as a dict-like to satisfy .get()
    import types
    mc_user = types.SimpleNamespace(op=types.SimpleNamespace(enabled=True, level=3))
    db.get_minecraft_user = lambda guild_id, user_id: mc_user
    assert db.has_op_level(1, 10, 2) is True
    assert db.has_op_level(1, 10, 4) is False

    # no user -> false
    db.get_minecraft_user = lambda guild_id, user_id: None
    assert db.has_op_level(1, 10, 2) is False
