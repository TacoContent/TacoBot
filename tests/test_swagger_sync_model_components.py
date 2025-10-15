"""Tests automatic model component schema extraction via @openapi.component.

Validates that the DiscordChannel model (decorated) is turned into an OpenAPI
component schema with expected property types and required list.
"""
from __future__ import annotations

import pathlib
import yaml

from scripts.swagger_sync import collect_model_components


def test_collect_model_components_discord_channel():
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)
    assert 'DiscordChannel' in comps, 'DiscordChannel component missing'
    schema = comps['DiscordChannel']
    props = schema['properties']
    # Core fields present
    for field in ['id', 'name', 'type', 'guild_id', 'position', 'nsfw']:
        assert field in props, f'Missing property: {field}'
    # Type assertions (heuristic mapping)
    assert props['id']['type'] == 'string'
    assert props['position']['type'] == 'integer'
    assert props['nsfw']['type'] == 'boolean'
    # Required list should include non-nullables
    required = set(schema.get('required', []))
    for field in ['id', 'name', 'type']:
        assert field in required, f'{field} should be required'


def test_collect_model_components_discord_message_list_of_dict_items_object():
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)
    assert 'DiscordMessage' in comps, 'DiscordMessage component missing'
    schema = comps['DiscordMessage']
    props = schema['properties']
    # Ensure embeds / mentions / attachments / reactions arrays use object item type (not string)
    for list_field in ['embeds', 'mentions', 'attachments', 'reactions']:
        assert list_field in props, f'Missing property: {list_field}'
        lf_schema = props[list_field]
        assert lf_schema['type'] == 'array', f'{list_field} should be array'
        assert lf_schema['items']['type'] == 'object', f'{list_field} items should be object (was {lf_schema["items"]["type"]})'


def test_collect_model_components_discord_emoji_literal_enum():
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)
    assert 'DiscordEmoji' in comps, 'DiscordEmoji component missing'
    schema = comps['DiscordEmoji']
    props = schema['properties']
    assert 'type' in props, 'DiscordEmoji.type property missing'
    type_schema = props['type']
    # Should still be type string
    assert type_schema['type'] == 'string'
    # Should include enum with the literal value 'emoji'
    assert 'enum' in type_schema, 'Enum not inferred for Literal field'
    assert type_schema['enum'] == ['emoji'], f"Unexpected enum values: {type_schema['enum']}"


def test_collect_model_components_join_whitelist_user_property_descriptions():
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)
    assert 'JoinWhitelistUser' in comps, 'JoinWhitelistUser component missing'
    schema = comps['JoinWhitelistUser']
    props = schema['properties']
    # Ensure metadata descriptions were applied
    assert props['guild_id'].get('description') == 'Discord guild (server) identifier scoping the whitelist entry.'
    assert props['user_id'].get('description') == 'Discord user identifier for the whitelisted user.'
    assert 'description' in props['added_by'], 'added_by description missing'
    assert 'description' in props['timestamp'], 'timestamp description missing'


def test_collect_model_components_metadata_merge_precedence():
    models_root = pathlib.Path('tests/tmp_model_components')
    comps, _ = collect_model_components(models_root)
    assert 'MergeMetadataExample' in comps, 'MergeMetadataExample component missing'
    schema = comps['MergeMetadataExample']
    props = schema['properties']
    # Legacy description preserved
    assert props['merged'].get('description') == 'description (should persist)'
    # Unified block added enum without overwriting description
    assert 'enum' in props['merged'] and props['merged']['enum'] == ['a', 'b', 'c'], 'Enum missing or incorrect'
    # Literal field enum from code takes precedence over both blocks
    assert 'enum' in props['literal'] and props['literal']['enum'] == ['simple'], 'Literal enum incorrect'
    # Property only in unified block present
    assert 'added_only_in_unified' in props, 'Unified-only property missing'
    # Legacy-only property present
    assert 'primary' in props and props['primary'].get('description') == 'Primary description from legacy block'


def test_collect_model_components_openapi_attributes():
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)
    assert 'MinecraftPlayerEvent' in comps, 'MinecraftPlayerEvent component missing'
    schema = comps['MinecraftPlayerEvent']
    assert schema.get('x-tacobot-managed') is True, 'managed attribute missing on schema'
    event_schema = schema['properties']['event']
    assert event_schema['type'] == 'string'
    assert event_schema.get('enum') == ['death', 'login', 'logout', 'unknown']


def test_collect_model_components_attribute_prefix_normalization():
    models_root = pathlib.Path('tests/tmp_model_components')
    comps, _ = collect_model_components(models_root)
    assert 'DecoratorAttributeExample' in comps, 'DecoratorAttributeExample component missing'
    schema = comps['DecoratorAttributeExample']
    assert schema.get('x-custom-flag') == 'enabled', 'Decorator attribute should be namespaced with x- prefix'


def test_collect_model_components_optional_dict_infers_object():
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)
    assert 'MinecraftPlayerEventPayload' in comps, 'MinecraftPlayerEventPayload component missing'
    schema = comps['MinecraftPlayerEventPayload']
    payload_schema = schema['properties']['payload']
    assert payload_schema['type'] == 'object', 'Optional dict annotation should map to object type'
    assert payload_schema.get('nullable') is True, 'Optional dict should remain nullable'
