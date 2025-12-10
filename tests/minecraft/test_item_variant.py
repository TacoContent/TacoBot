from bot.lib.minecraft.item import calculate_variant_id, calculate_variant_id_from_snbt


def test_calculate_variant_id_from_dict():
    expected = "a395b124c58e76569b695214eb532bbb979b8fa5fbeaa49d92778c7a73aac49a"
    # Construct the nested dict representation of the provided NBT
    item_id = "minecraft:netherite_boots"
    nbt = {
        "components": {
            "minecraft:enchantments": {"levels": {"minecraft:fortune": 6, "minecraft:unbreaking": 6}}
        }
    }

    got = calculate_variant_id(item_id, nbt)
    assert isinstance(got, str) and len(got) == 64
    assert got == expected


def test_calculate_variant_id_from_snbt_string():
    expected = "a395b124c58e76569b695214eb532bbb979b8fa5fbeaa49d92778c7a73aac49a"
    # The user-provided SNBT string (lowercase count will be normalized by helper)
    item_id = "minecraft:netherite_boots"
    snbt = '{components:{"minecraft:enchantments":{levels:{"minecraft:fortune":6,"minecraft:unbreaking":6}}},count:1,id:"minecraft:netherite_boots"}'
    got = calculate_variant_id_from_snbt(item_id, snbt)
    assert got == expected


def test_empty_snbt_uses_item_id():
    item_id = "minecraft:netherite_boots"
    # None, empty string and '{}' should be treated as the same minimal SNBT
    assert calculate_variant_id_from_snbt(item_id, None) == calculate_variant_id(item_id, None)
    assert calculate_variant_id_from_snbt(item_id, "") == calculate_variant_id(item_id, None)
    assert calculate_variant_id_from_snbt(item_id, "{}") == calculate_variant_id(item_id, None)


def test_dragon_egg_variants_equivalent():
    item_id = "minecraft:dragon_egg"
    expected = "453e3e25e8500728b41b35fa69f0dc4020ec385661175cf9669098ff6ca10d64"

    # SNBT with count:2 should normalize to count:1 for hashing
    snbt_count2 = '{count:2,id:"minecraft:dragon_egg"}'
    assert calculate_variant_id_from_snbt(item_id, snbt_count2) == expected

    # empty string -> uses default count 1 and id
    assert calculate_variant_id_from_snbt(item_id, "") == expected

    # explicit count:1 should match
    snbt_count1 = 'count:1,id:"minecraft:dragon_egg"'
    assert calculate_variant_id_from_snbt(item_id, snbt_count1) == expected

    # And dict-style should also match when passing None (defaults)
    assert calculate_variant_id(item_id, None) == expected


def test_missing_id_is_added_for_snbt():
    item_id = "minecraft:diamond_helmet"
    expected = "606635a7baefc2facf1e5e13c6d0064d1a3c377da1347aedcbf5a6c7542b5047"

    # SNBT missing id field but with components and count — id should be injected
    snbt_missing_id = '{components:{"minecraft:damage":37},count:1}'
    got = calculate_variant_id_from_snbt(item_id, snbt_missing_id)
    assert got == expected

    # dict-style should match when nbt passed
    nbt = {"components": {"minecraft:damage": 37}}
    assert calculate_variant_id(item_id, nbt) == expected


def test_shulker_box_with_contents():
    item_id = 'minecraft:shulker_box'
    snbt = '{components:{"minecraft:container":[{item:{count:64,id:"minecraft:dirt"},slot:0},{item:{count:1,id:"minecraft:iron_helmet"},slot:1},{item:{count:5,id:"minecraft:apple"},slot:2},{item:{count:3,id:"minecraft:stick"},slot:3},{item:{count:4,id:"minecraft:coal"},slot:4}]},count:1,id:"minecraft:shulker_box"}'
    expected = '376f09b92e89f3c3225d1f7f2e049a3621b14a4404c17d8937b8d7b6fe967977'
    assert calculate_variant_id_from_snbt(item_id, snbt) == expected


def test_deterministic_ordering_is_independent_of_input_order():
    expected = "a395b124c58e76569b695214eb532bbb979b8fa5fbeaa49d92778c7a73aac49a"
    item_id = "minecraft:netherite_boots"
    # Put keys in a different input order to simulate non-deterministic dict ordering
    nbt_a = {"components": {"minecraft:enchantments": {"levels": {"minecraft:unbreaking": 6, "minecraft:fortune": 6}}}}
    nbt_b = {"components": {"minecraft:enchantments": {"levels": {"minecraft:fortune": 6, "minecraft:unbreaking": 6}}}}

    assert calculate_variant_id(item_id, nbt_a) == calculate_variant_id(item_id, nbt_b) == expected
