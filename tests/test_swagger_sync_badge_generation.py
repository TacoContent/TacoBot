"""Tests for swagger_sync.badge.generate_coverage_badge function.

Covers:
 - Badge generation with different coverage percentages
 - Color coding verification (red, yellow, green)
 - SVG output format validation
 - Directory creation
 - Error handling
"""

from __future__ import annotations

import pathlib
import re
import tempfile
import xml.etree.ElementTree as ET

import pytest

from scripts.swagger_sync.badge import generate_coverage_badge


def test_badge_generation_green_high_coverage():
    """Test badge generation with high coverage (>= 80%) produces green color."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.95, output_path)

        assert output_path.exists(), "Badge file should be created"
        content = output_path.read_text(encoding='utf-8')

        # Verify it's valid SVG
        assert content.startswith('<svg'), "Should be SVG format"
        assert 'xmlns="http://www.w3.org/2000/svg"' in content, "Should have SVG namespace"

        # Verify percentage display
        assert '95.0%' in content, "Should show correct percentage"
        assert 'OpenAPI Coverage' in content, "Should show label"

        # Verify green color (#4c1)
        assert 'fill="#4c1"' in content, "Should use green color for high coverage"


def test_badge_generation_yellow_medium_coverage():
    """Test badge generation with medium coverage (50-79%) produces yellow color."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.65, output_path)

        content = output_path.read_text(encoding='utf-8')

        # Verify percentage display
        assert '65.0%' in content, "Should show correct percentage"

        # Verify yellow color (#dfb317)
        assert 'fill="#dfb317"' in content, "Should use yellow color for medium coverage"


def test_badge_generation_red_low_coverage():
    """Test badge generation with low coverage (< 50%) produces red color."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.35, output_path)

        content = output_path.read_text(encoding='utf-8')

        # Verify percentage display
        assert '35.0%' in content, "Should show correct percentage"

        # Verify red color (#e05d44)
        assert 'fill="#e05d44"' in content, "Should use red color for low coverage"


def test_badge_generation_boundary_50_percent():
    """Test badge generation at 50% boundary (should be yellow)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.50, output_path)

        content = output_path.read_text(encoding='utf-8')
        assert '50.0%' in content
        assert 'fill="#dfb317"' in content, "50% should be yellow (inclusive lower bound)"


def test_badge_generation_boundary_80_percent():
    """Test badge generation at 80% boundary (should be green)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.80, output_path)

        content = output_path.read_text(encoding='utf-8')
        assert '80.0%' in content
        assert 'fill="#4c1"' in content, "80% should be green (inclusive lower bound)"


def test_badge_generation_zero_coverage():
    """Test badge generation with 0% coverage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.0, output_path)

        content = output_path.read_text(encoding='utf-8')
        assert '0.0%' in content
        assert 'fill="#e05d44"' in content, "0% should be red"


def test_badge_generation_perfect_coverage():
    """Test badge generation with 100% coverage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(1.0, output_path)

        content = output_path.read_text(encoding='utf-8')
        assert '100.0%' in content
        assert 'fill="#4c1"' in content, "100% should be green"


def test_badge_generation_creates_directory():
    """Test that badge generation creates parent directories if they don't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'nested' / 'directories' / 'badge.svg'

        # Verify directory doesn't exist yet
        assert not output_path.parent.exists()

        generate_coverage_badge(0.75, output_path)

        # Verify directory was created
        assert output_path.parent.exists(), "Parent directories should be created"
        assert output_path.exists(), "Badge file should be created"


def test_badge_generation_valid_xml_structure():
    """Test that generated badge is valid XML/SVG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.85, output_path)

        # Parse as XML to verify structure
        tree = ET.parse(output_path)
        root = tree.getroot()

        # Verify it's an SVG element (with namespace)
        assert 'svg' in root.tag, "Root element should be svg"

        # Verify required attributes (namespace is in tag, not as attribute in ElementTree)
        assert '{http://www.w3.org/2000/svg}' in root.tag or root.tag == 'svg'
        assert root.get('width') is not None
        assert root.get('height') is not None
        assert root.get('role') == 'img'

        # Verify aria-label contains coverage info
        aria_label = root.get('aria-label')
        assert aria_label is not None
        assert 'OpenAPI Coverage' in aria_label
        assert '85.0%' in aria_label

        # Verify xmlns is present in the raw content (ElementTree handles it differently)
        content = output_path.read_text(encoding='utf-8')
        assert 'xmlns="http://www.w3.org/2000/svg"' in content


def test_badge_generation_title_element():
    """Test that badge includes a title element for accessibility."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.92, output_path)

        content = output_path.read_text(encoding='utf-8')

        # Check for title element
        assert '<title>OpenAPI Coverage: 92.0%</title>' in content


def test_badge_generation_text_content():
    """Test that badge contains correct text content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.88, output_path)

        content = output_path.read_text(encoding='utf-8')

        # Check for text content (label and percentage)
        # The text appears in both visible and shadow (aria-hidden) versions
        assert content.count('OpenAPI Coverage') >= 2, "Label should appear at least twice"
        assert content.count('88.0%') >= 2, "Percentage should appear at least twice"


def test_badge_generation_overwrite_existing():
    """Test that badge generation overwrites existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'

        # Create initial badge with 50%
        generate_coverage_badge(0.50, output_path)
        content1 = output_path.read_text(encoding='utf-8')
        assert '50.0%' in content1
        assert 'fill="#dfb317"' in content1  # Yellow

        # Overwrite with 90%
        generate_coverage_badge(0.90, output_path)
        content2 = output_path.read_text(encoding='utf-8')
        assert '90.0%' in content2
        assert 'fill="#4c1"' in content2  # Green
        assert '50.0%' not in content2, "Old percentage should be replaced"


def test_badge_generation_fractional_percentages():
    """Test badge generation with various fractional coverage values."""
    test_cases = [(0.123, '12.3%'), (0.456, '45.6%'), (0.789, '78.9%'), (0.999, '99.9%')]

    with tempfile.TemporaryDirectory() as tmpdir:
        for coverage, expected_text in test_cases:
            output_path = pathlib.Path(tmpdir) / f'badge-{coverage}.svg'
            generate_coverage_badge(coverage, output_path)
            content = output_path.read_text(encoding='utf-8')
            assert expected_text in content, f"Should show {expected_text} for coverage {coverage}"


def test_badge_generation_consistent_dimensions():
    """Test that badges have consistent dimensions regardless of percentage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dimensions = []
        for coverage in [0.0, 0.5, 1.0]:
            output_path = pathlib.Path(tmpdir) / f'badge-{coverage}.svg'
            generate_coverage_badge(coverage, output_path)

            tree = ET.parse(output_path)
            root = tree.getroot()
            width = root.get('width')
            height = root.get('height')
            dimensions.append((width, height))

        # All badges should have same height
        heights = [h for _, h in dimensions]
        assert all(h == heights[0] for h in heights), "All badges should have same height"

        # Height should be 20 (standard badge height)
        assert heights[0] == '20', "Badge height should be 20"


def test_badge_color_thresholds_comprehensive():
    """Comprehensive test of color threshold boundaries."""
    test_cases = [
        # (coverage, expected_color, color_name)
        (0.00, '#e05d44', 'red'),
        (0.25, '#e05d44', 'red'),
        (0.49, '#e05d44', 'red'),
        (0.499, '#e05d44', 'red'),
        (0.50, '#dfb317', 'yellow'),
        (0.65, '#dfb317', 'yellow'),
        (0.79, '#dfb317', 'yellow'),
        (0.799, '#dfb317', 'yellow'),
        (0.80, '#4c1', 'green'),
        (0.90, '#4c1', 'green'),
        (1.00, '#4c1', 'green'),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        for coverage, expected_color, color_name in test_cases:
            output_path = pathlib.Path(tmpdir) / f'badge-{coverage}.svg'
            generate_coverage_badge(coverage, output_path)
            content = output_path.read_text(encoding='utf-8')
            assert (
                f'fill="{expected_color}"' in content
            ), f"Coverage {coverage:.1%} should use {color_name} color ({expected_color})"


def test_badge_utf8_encoding():
    """Test that badge is written with UTF-8 encoding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = pathlib.Path(tmpdir) / 'test-badge.svg'
        generate_coverage_badge(0.75, output_path)

        # Read as bytes and verify encoding
        content_bytes = output_path.read_bytes()

        # Should decode as UTF-8 without errors
        content_str = content_bytes.decode('utf-8')
        assert '75.0%' in content_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
