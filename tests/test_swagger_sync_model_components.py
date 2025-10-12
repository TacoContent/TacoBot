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
