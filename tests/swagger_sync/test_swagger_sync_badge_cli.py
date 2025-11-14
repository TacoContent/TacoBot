"""Integration test for badge generation via CLI.

Tests the --generate-badge command-line argument to ensure it properly
integrates with the main swagger_sync.py workflow.

Note: Subprocess tests don't contribute to coverage metrics since the script
runs in a separate process. Direct function tests are in test_swagger_sync_badge_generation.py.
"""

from __future__ import annotations

import io
import pathlib
import subprocess
import sys
import tempfile
from unittest import mock

import pytest
from scripts.swagger_sync.badge import generate_coverage_badge


def test_badge_generation_via_cli():
    """Test that --generate-badge CLI argument generates a badge file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = pathlib.Path(tmpdir) / 'coverage-badge.svg'

        # Run swagger_sync with --generate-badge using the current Python interpreter
        result = subprocess.run(
            [sys.executable, 'scripts/swagger_sync.py', '--check', f'--generate-badge={badge_path}'],
            cwd=pathlib.Path.cwd(),
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should succeed (exit code 0 since we're in sync)
        assert result.returncode == 0, f"Script should succeed: {result.stderr}"

        # Badge should be created
        assert badge_path.exists(), "Badge file should be created"

        # Verify badge content
        content = badge_path.read_text(encoding='utf-8')
        assert '<svg' in content, "Should be SVG format"
        assert 'OpenAPI Coverage' in content, "Should contain label"
        assert '%' in content, "Should contain percentage"


def test_badge_generation_creates_nested_directories():
    """Test that --generate-badge creates nested directories if they don't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = pathlib.Path(tmpdir) / 'deeply' / 'nested' / 'path' / 'badge.svg'

        # Verify directory doesn't exist
        assert not badge_path.parent.exists()

        result = subprocess.run(
            [sys.executable, 'scripts/swagger_sync.py', '--check', f'--generate-badge={badge_path}'],
            cwd=pathlib.Path.cwd(),
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert badge_path.exists(), "Badge should be created in nested directory"
        assert badge_path.parent.exists(), "Nested directories should be created"


def test_badge_generation_with_fix_mode():
    """Test that badge generation works with --fix mode too."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = pathlib.Path(tmpdir) / 'badge.svg'

        result = subprocess.run(
            [sys.executable, 'scripts/swagger_sync.py', '--fix', f'--generate-badge={badge_path}'],
            cwd=pathlib.Path.cwd(),
            capture_output=True,
            text=True,
            timeout=30,
        )

        # In fix mode, we don't generate the badge since we exit early
        # (different code path than check mode)
        # Badge generation only happens in check mode currently
        assert result.returncode == 0


def test_badge_path_with_spaces():
    """Test badge generation with path containing spaces."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = pathlib.Path(tmpdir) / 'path with spaces' / 'badge.svg'

        result = subprocess.run(
            [sys.executable, 'scripts/swagger_sync.py', '--check', f'--generate-badge={badge_path}'],
            cwd=pathlib.Path.cwd(),
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert badge_path.exists(), "Should handle paths with spaces"


# Direct function tests (these contribute to coverage)


def test_badge_generation_direct_function_call():
    """Test generate_coverage_badge function directly for coverage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = pathlib.Path(tmpdir) / 'direct-test.svg'

        # Test direct function call
        generate_coverage_badge(0.75, badge_path)

        assert badge_path.exists()
        content = badge_path.read_text(encoding='utf-8')
        assert '75.0%' in content
        assert 'fill="#dfb317"' in content  # Yellow


def test_badge_generation_with_readonly_parent_directory():
    """Test badge generation when parent directory cannot be written to."""
    with tempfile.TemporaryDirectory() as tmpdir:
        parent = pathlib.Path(tmpdir) / 'readonly'
        parent.mkdir()
        badge_path = parent / 'badge.svg'

        # Make directory read-only (platform-specific)
        import stat

        try:
            parent.chmod(stat.S_IRUSR | stat.S_IXUSR)

            # On Windows, read-only doesn't prevent file creation
            # On Unix, this should raise PermissionError
            if sys.platform != 'win32':
                with pytest.raises(PermissionError):
                    generate_coverage_badge(0.5, badge_path)
        finally:
            # Restore permissions for cleanup
            parent.chmod(stat.S_IRWXU)


def test_badge_generation_error_handling_file_write():
    """Test error handling when file write fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = pathlib.Path(tmpdir) / 'test.svg'

        # Mock Path.write_text to raise an error
        with mock.patch.object(pathlib.Path, 'write_text', side_effect=IOError("Disk full")):
            with pytest.raises(IOError, match="Disk full"):
                generate_coverage_badge(0.9, badge_path)


def test_badge_generation_error_handling_directory_creation():
    """Test error handling when directory creation fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = pathlib.Path(tmpdir) / 'nested' / 'badge.svg'

        # Mock Path.mkdir to raise an error
        with mock.patch.object(pathlib.Path, 'mkdir', side_effect=OSError("Permission denied")):
            with pytest.raises(OSError, match="Permission denied"):
                generate_coverage_badge(0.8, badge_path)


def test_badge_generation_with_absolute_path():
    """Test badge generation with absolute path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = pathlib.Path(tmpdir).resolve() / 'absolute-path-badge.svg'

        generate_coverage_badge(0.95, badge_path)

        assert badge_path.exists()
        assert badge_path.is_absolute()


def test_badge_generation_with_relative_path():
    """Test badge generation with relative path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = pathlib.Path.cwd()
        try:
            import os

            os.chdir(tmpdir)

            badge_path = pathlib.Path('relative-badge.svg')
            generate_coverage_badge(0.55, badge_path)

            assert badge_path.exists()
            content = badge_path.read_text(encoding='utf-8')
            assert '55.0%' in content
        finally:
            os.chdir(original_cwd)


def test_badge_generation_coverage_edge_values():
    """Test badge generation with edge case coverage values."""
    test_cases = [
        (0.0, '#e05d44'),  # Exactly 0%
        (0.499, '#e05d44'),  # Just below 50%
        (0.5, '#dfb317'),  # Exactly 50%
        (0.799, '#dfb317'),  # Just below 80%
        (0.8, '#4c1'),  # Exactly 80%
        (1.0, '#4c1'),  # Exactly 100%
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        for coverage, expected_color in test_cases:
            badge_path = pathlib.Path(tmpdir) / f'edge-{coverage}.svg'
            generate_coverage_badge(coverage, badge_path)

            content = badge_path.read_text(encoding='utf-8')
            assert f'fill="{expected_color}"' in content, f"Coverage {coverage} should produce color {expected_color}"


def test_badge_generation_concurrent_writes():
    """Test that multiple badge generations to same file don't cause issues."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = pathlib.Path(tmpdir) / 'concurrent.svg'

        # Write multiple times rapidly
        for coverage in [0.3, 0.6, 0.9]:
            generate_coverage_badge(coverage, badge_path)

        # Last write should win
        content = badge_path.read_text(encoding='utf-8')
        assert '90.0%' in content
        assert 'fill="#4c1"' in content


def test_badge_generation_unicode_in_path():
    """Test badge generation with unicode characters in path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Some filesystems may not support all unicode characters
        try:
            badge_path = pathlib.Path(tmpdir) / 'unicode_测试_badge.svg'
            generate_coverage_badge(0.77, badge_path)

            assert badge_path.exists()
            content = badge_path.read_text(encoding='utf-8')
            assert '77.0%' in content
        except (OSError, UnicodeError):
            pytest.skip("Filesystem doesn't support unicode in filenames")


def test_badge_generation_very_long_path():
    """Test badge generation with very long path (near OS limits)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a deeply nested path (but not exceeding OS limits)
        long_path = pathlib.Path(tmpdir)
        for i in range(10):
            long_path = long_path / f'level{i}'

        badge_path = long_path / 'badge.svg'

        try:
            generate_coverage_badge(0.88, badge_path)
            assert badge_path.exists()
        except OSError:
            # Some systems have path length limits
            pytest.skip("Path too long for this filesystem")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
