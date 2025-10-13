"""Tests automatic model component schema extraction via @openapi_model.

Validates that the DiscordChannel model (decorated) is turned into an OpenAPI
component schema with expected property types and required list.
"""
from __future__ import annotations

import pathlib
import yaml

from scripts.swagger_sync import collect_model_components


def test_collect_model_components_discord_channel():
    models_root = pathlib.Path('bot/lib/models')
    comps = collect_model_components(models_root)
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
    comps = collect_model_components(models_root)
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
    comps = collect_model_components(models_root)
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
