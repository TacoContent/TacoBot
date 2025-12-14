import hashlib

from bot.lib.minecraft.item import calculate_variant_id, calculate_variant_id_from_snbt, canonicalize_snbt


def test_calculate_variant_id_from_snbt_sorts_top_level_and_nested():
    item = "minecraft:netherite_leggings"
    # Provided SNBT with keys in arbitrary order (id at front)
    snbt = '{id:"minecraft:netherite_leggings",components:{"minecraft:enchantments":{levels:{"minecraft:unbreaking":6,"minecraft:fortune":6}}},count:1}'

    expected_sorted = '{components:{"minecraft:enchantments":{levels:{"minecraft:fortune":6,"minecraft:unbreaking":6}}},count:1,id:"minecraft:netherite_leggings"}'

    got_digest = calculate_variant_id_from_snbt(item, snbt)
    expected_digest_via_snbt = calculate_variant_id_from_snbt(item, expected_sorted)
    # SNBT normalization should be idempotent (sorted input yields same digest)
    assert got_digest == expected_digest_via_snbt

    # Also assert the canonical string is exactly as we expect
    canon = canonicalize_snbt(item, snbt)
    assert canon == expected_sorted

    # Equivalent dict input should produce the same digest
    nbt = {
        "components": {
            "minecraft:enchantments": {"levels": {"minecraft:fortune": 6, "minecraft:unbreaking": 6}}
        }
    }
    dict_digest = calculate_variant_id(item, nbt)
    assert dict_digest == got_digest
