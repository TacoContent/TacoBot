"""Test orphan detection for components."""

from scripts.swagger_sync import detect_orphans, Endpoint
import pathlib


def test_detect_orphans_includes_components():
    """Test that detect_orphans includes components that exist in swagger but not in model classes."""
    # Create mock swagger with components
    swagger = {
        'paths': {
            '/api/v1/test': {
                'get': {'summary': 'Test endpoint'}
            }
        },
        'components': {
            'schemas': {
                'TestModel': {'type': 'object'},
                'OrphanModel': {'type': 'object'},
                'AnotherOrphan': {'type': 'object'}
            }
        }
    }

    # Create mock endpoint that exists
    endpoints = [
        Endpoint(
            path='/api/v1/test',
            method='get',
            meta={'summary': 'Test endpoint'},
            function='test_handler',
            file=pathlib.Path('test.py')
        )
    ]

    # Create mock model components (only one exists)
    model_components = {
        'TestModel': {'type': 'object', 'properties': {}}
    }

    # Test orphan detection
    orphans = detect_orphans(swagger, endpoints, model_components)

    # Should detect orphaned components
    orphan_components = [o for o in orphans if 'Component present only in swagger' in o]
    assert len(orphan_components) == 2
    assert any('OrphanModel' in o for o in orphan_components)
    assert any('AnotherOrphan' in o for o in orphan_components)

    # Should not detect path orphans since the path exists
    path_orphans = [o for o in orphans if 'Path present only in swagger' in o]
    assert len(path_orphans) == 0


def test_detect_orphans_no_model_components():
    """Test that detect_orphans works when model_components is None."""
    swagger = {
        'paths': {
            '/api/v1/missing': {
                'get': {'summary': 'Missing endpoint'}
            }
        },
        'components': {
            'schemas': {
                'SomeModel': {'type': 'object'}
            }
        }
    }

    endpoints = []  # No endpoints

    # Test with None model_components (should not check components)
    orphans = detect_orphans(swagger, endpoints, None)

    # Should only detect path orphans, not component orphans
    assert len(orphans) == 1
    assert 'Path present only in swagger' in orphans[0]
    assert 'missing' in orphans[0]


def test_detect_orphans_empty_components():
    """Test that detect_orphans handles empty components gracefully."""
    swagger = {
        'paths': {},
        'components': {
            'schemas': {}
        }
    }

    endpoints = []
    model_components = {}

    orphans = detect_orphans(swagger, endpoints, model_components)
    assert len(orphans) == 0


def test_detect_orphans_no_components_section():
    """Test that detect_orphans handles swagger without components section."""
    swagger = {
        'paths': {
            '/api/v1/test': {
                'get': {'summary': 'Test'}
            }
        }
    }

    endpoints = []
    model_components = {}

    orphans = detect_orphans(swagger, endpoints, model_components)

    # Should only detect path orphan
    assert len(orphans) == 1
    assert 'Path present only in swagger' in orphans[0]
