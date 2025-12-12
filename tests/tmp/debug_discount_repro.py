from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.models.MinecraftUserEntry import MinecraftUserEntry
import types
from unittest.mock import MagicMock

print('starting quick repro')
db = MinecraftDatabase()
db.get_minecraft_user = MagicMock(return_value=MinecraftUserEntry(guild_id=1, user_id='123456789', role_ids=[]))
db.settings = types.SimpleNamespace(get_settings=MagicMock(return_value={'storage':{'initial_slots':9,'increase_cost':1000},'discounts':[{'user_id':123456789,'roles':[],'discount':0.1,'expires':None}]}))
print('call get_user_shop_discount')
res = db.get_user_shop_discount(guild_id=1, user_id='123456789')
print('result', res)
# iterate discounts externally to validate
s = db.settings.get_settings()
print('external iterate discounts ->', list(s.get('discounts', [])))
