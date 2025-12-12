
# storage: {
#     initial_slots: 9,
#     increase_cost: 1000
# },
# discount: [
#     {
#         user_id: '262031734260891648',
#         roles: [],
#         amount: 0.1,
#         expires: null
#     }
# ]


import typing


class MinecraftShopSettings:
    def __init__(self, **kwargs):
        storage_kwargs = kwargs.get('storage', {})
        discount_kwargs = kwargs.get('discount', [])
        self.storage: MinecraftShopSettingsStorage = MinecraftShopSettingsStorage(**storage_kwargs)
        self.discounts: typing.List[MinecraftShopSettingsDiscount] = [
            MinecraftShopSettingsDiscount(**d) for d in discount_kwargs
        ]

    def to_dict(self):
        return {
            'storage': self.storage.to_dict(),
            'discount': [d.to_dict() for d in self.discounts]
        }

class MinecraftShopSettingsDiscount:
    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id', None)
        self.roles = [str(r) for r in kwargs.get('roles', [])]
        self.discount = kwargs.get('discount', 0.0)
        self.expires = kwargs.get('expires', None)

    def is_empty(self):
        return not self.user_id and self.user_id != ''

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'roles': [str(r) for r in self.roles],
            'discount': self.discount,
            'expires': self.expires
        }

class MinecraftShopSettingsStorage:
    def __init__(self, **kwargs):
        self.initial_slots = kwargs.get('initial_slots', 9)
        self.increase_cost = kwargs.get('increase_cost', 1000)
        self.increase_slots_by = kwargs.get('increase_slots_by', 9)

        #
        self.discount = kwargs.get('discount', 0.0)
        self.original_increase_cost = kwargs.get('original_increase_cost', self.increase_cost)

    def to_dict(self):
        return {
            'initial_slots': self.initial_slots,
            'increase_cost': self.increase_cost,
            'increase_slots_by': self.increase_slots_by,
            'discount': self.discount

        }
