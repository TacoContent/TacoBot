"""
Test union type handling and oneOf schema generation.

Tests the swagger_sync.py script's ability to:
- Detect TypeAlias with Union types
- Generate oneOf schemas from Union[A, B] syntax
- Handle separate openapi.type_alias decorator calls
- Support managed flag and custom attributes on union types
"""

import pathlib

from scripts.swagger_sync import collect_model_components


def test_discord_mentionable_union_type():
    """Test real-world DiscordMentionable pattern generates oneOf schema."""
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)

    # Verify DiscordMentionable exists and has oneOf
    assert 'DiscordMentionable' in comps, 'DiscordMentionable component missing'
    schema = comps['DiscordMentionable']

    # Check oneOf structure
    assert 'oneOf' in schema, 'oneOf key missing from DiscordMentionable schema'
    assert len(schema['oneOf']) == 2, f'Expected 2 oneOf items, got {len(schema["oneOf"])}'

    # Check that refs are correct
    refs = [item.get('$ref') for item in schema['oneOf']]
    assert '#/components/schemas/DiscordRole' in refs, 'DiscordRole ref missing'
    assert '#/components/schemas/DiscordUser' in refs, 'DiscordUser ref missing'

    # Check metadata
    assert schema.get('description') == 'Represents a Discord mentionable entity.'
    assert schema.get('x-tacobot-managed') is True


def test_union_type_preserves_managed_flag():
    """Verify managed flag is preserved in union schemas."""
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)

    if 'DiscordMentionable' in comps:
        schema = comps['DiscordMentionable']
        # Managed types should have the x-tacobot-managed extension
        assert schema.get('x-tacobot-managed') is True


def test_union_schema_no_primitive_refs():
    """Verify that union oneOf only includes object refs, no primitive types."""
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)

    if 'DiscordMentionable' in comps:
        schema = comps['DiscordMentionable']
        one_of_list = schema.get('oneOf', [])

        # All oneOf items should be $ref to schema objects
        for item in one_of_list:
            assert '$ref' in item, f'oneOf item missing $ref: {item}'
            ref_path = item['$ref']
            assert ref_path.startswith('#/components/schemas/'), f'Invalid ref format: {ref_path}'

            # Schema name should be capitalized (model class pattern)
            schema_name = ref_path.split('/')[-1]
            assert schema_name[0].isupper(), f'Schema name should be capitalized: {schema_name}'


def test_union_type_no_duplicates():
    """Verify union oneOf does not contain duplicate refs."""
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)

    if 'DiscordMentionable' in comps:
        schema = comps['DiscordMentionable']
        one_of_list = schema.get('oneOf', [])
        refs = [item.get('$ref') for item in one_of_list]

        # Check for duplicates
        assert len(refs) == len(set(refs)), f'Duplicate refs found in oneOf: {refs}'


def test_union_uses_oneof_not_allof():
    """Verify union types use oneOf (not allOf or anyOf)."""
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)

    if 'DiscordMentionable' in comps:
        schema = comps['DiscordMentionable']

        # Should use oneOf for union types
        assert 'oneOf' in schema, 'Union type should use oneOf'

        # Should NOT use allOf or anyOf for simple unions
        assert 'allOf' not in schema, 'Union type should not use allOf'
        assert 'anyOf' not in schema, 'Union type should not use anyOf'


def test_search_criteria_uses_anyof():
    """Verify anyof=True generates anyOf instead of oneOf."""
    models_root = pathlib.Path('tests')
    comps, _ = collect_model_components(models_root)

    # Verify SearchCriteria exists and uses anyOf
    assert 'SearchCriteria' in comps, 'SearchCriteria component missing'
    schema = comps['SearchCriteria']

    # Should use anyOf when anyof flag is set
    assert 'anyOf' in schema, 'anyOf key missing from SearchCriteria schema'
    assert 'oneOf' not in schema, 'Should use anyOf not oneOf when anyof=True'
    assert 'allOf' not in schema, 'Should not use allOf'

    # Check that it has the correct refs
    any_of_list = schema['anyOf']
    assert len(any_of_list) == 3, f'Expected 3 anyOf items, got {len(any_of_list)}'

    refs = [item.get('$ref') for item in any_of_list]
    assert '#/components/schemas/SearchDateFilter' in refs, 'SearchDateFilter ref missing'
    assert '#/components/schemas/SearchAuthorFilter' in refs, 'SearchAuthorFilter ref missing'
    assert '#/components/schemas/SearchTagFilter' in refs, 'SearchTagFilter ref missing'

    # Check metadata
    assert (
        schema.get('description')
        == 'Search filters that can be combined - supports date range, author, and/or tag filters.'
    )
    assert schema.get('x-tacobot-managed') is True


def test_anyof_vs_oneof_distinction():
    """Verify that anyof=True and anyof=False produce different results."""
    # Check production models for DiscordMentionable
    prod_models_root = pathlib.Path('bot/lib/models')
    prod_comps, _ = collect_model_components(prod_models_root)

    # DiscordMentionable should use oneOf (default)
    if 'DiscordMentionable' in prod_comps:
        mentionable_schema = prod_comps['DiscordMentionable']
        assert 'oneOf' in mentionable_schema, 'Default should be oneOf'
        assert 'anyOf' not in mentionable_schema, 'Default should not be anyOf'

    # SearchCriteria is now in tests directory
    test_models_root = pathlib.Path('tests')
    test_comps, _ = collect_model_components(test_models_root)

    if 'SearchCriteria' in test_comps:
        search_schema = test_comps['SearchCriteria']
        assert 'anyOf' in search_schema, 'anyof=True should generate anyOf'
        assert 'oneOf' not in search_schema, 'anyof=True should not generate oneOf'


def test_optional_union_oneof_with_nullable():
    """Verify Optional[Union[...]] generates oneOf with nullable: true."""
    # Scan tests directory for test models
    models_root = pathlib.Path('tests')
    comps, _ = collect_model_components(models_root)

    # OptionalMentionable should exist
    assert 'OptionalMentionable' in comps, 'OptionalMentionable component missing'
    schema = comps['OptionalMentionable']

    # Should use oneOf (discriminated union)
    assert 'oneOf' in schema, 'Optional[Union[...]] should use oneOf'
    assert 'anyOf' not in schema, 'Should not use anyOf for discriminated union'

    # Should have nullable: true
    assert schema.get('nullable') is True, 'Optional[Union[...]] should have nullable: true'

    # Check refs
    one_of_list = schema['oneOf']
    assert len(one_of_list) == 2, f'Expected 2 oneOf items, got {len(one_of_list)}'

    refs = [item.get('$ref') for item in one_of_list]
    assert '#/components/schemas/DiscordRole' in refs, 'DiscordRole ref missing'
    assert '#/components/schemas/DiscordUser' in refs, 'DiscordUser ref missing'

    # Check metadata
    assert schema.get('description') == 'An optional Discord mentionable entity (role, user, or null).'
    assert schema.get('x-tacobot-managed') is True


def test_union_with_none_anyof_nullable():
    """Verify Union[A, B, C, None] with anyof=True generates anyOf with nullable: true."""
    # Scan tests directory for test models
    models_root = pathlib.Path('tests')
    comps, _ = collect_model_components(models_root)

    # OptionalSearchCriteria should exist
    assert 'OptionalSearchCriteria' in comps, 'OptionalSearchCriteria component missing'
    schema = comps['OptionalSearchCriteria']

    # Should use anyOf (composable filters)
    assert 'anyOf' in schema, 'Union with anyof=True should use anyOf'
    assert 'oneOf' not in schema, 'Should not use oneOf when anyof=True'

    # Should have nullable: true (because of None in union)
    assert schema.get('nullable') is True, 'Union[..., None] should have nullable: true'

    # Check refs
    any_of_list = schema['anyOf']
    assert len(any_of_list) == 3, f'Expected 3 anyOf items, got {len(any_of_list)}'

    refs = [item.get('$ref') for item in any_of_list]
    assert '#/components/schemas/SearchDateFilter' in refs, 'SearchDateFilter ref missing'
    assert '#/components/schemas/SearchAuthorFilter' in refs, 'SearchAuthorFilter ref missing'
    assert '#/components/schemas/SearchTagFilter' in refs, 'SearchTagFilter ref missing'

    # Check metadata
    assert 'Optional search filters' in schema.get('description', ''), 'Description should mention optional'
    assert schema.get('x-tacobot-managed') is True


def test_nullable_not_present_on_non_optional():
    """Verify non-optional unions do not have nullable: true."""
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)

    # DiscordMentionable (not optional) should NOT have nullable
    if 'DiscordMentionable' in comps:
        schema = comps['DiscordMentionable']
        assert schema.get('nullable') is not True, 'Non-optional union should not have nullable: true'

    # SearchCriteria (not optional) should NOT have nullable
    if 'SearchCriteria' in comps:
        schema = comps['SearchCriteria']
        assert schema.get('nullable') is not True, 'Non-optional union should not have nullable: true'


def test_optional_union_models_not_in_production():
    """Verify that optional union test models don't appear in production model scans."""
    # Scan production models directory
    models_root = pathlib.Path('bot/lib/models')
    comps, _ = collect_model_components(models_root)

    # Test models should NOT appear in production
    assert 'OptionalMentionable' not in comps, 'OptionalMentionable should not appear in production models'
    assert 'OptionalSearchCriteria' not in comps, 'OptionalSearchCriteria should not appear in production models'
