"""Badge generation for OpenAPI coverage visualization.

This module provides SVG badge generation functionality for displaying
OpenAPI documentation coverage metrics in README files and dashboards.
"""

from __future__ import annotations

import pathlib


def generate_coverage_badge(coverage_rate: float, output_path: pathlib.Path) -> None:
    """
    Generate an SVG badge showing OpenAPI documentation coverage percentage.

    Args:
        coverage_rate: Coverage percentage as a float (0.0 to 1.0)
        output_path: Path where the SVG badge should be written

    The badge uses color coding:
    - Red (#e05d44): coverage < 50%
    - Yellow (#dfb317): 50% <= coverage < 80%
    - Green (#4c1): coverage >= 80%
    """
    # Convert to percentage
    percentage = coverage_rate * 100

    # Determine color based on coverage
    if percentage < 50:
        color = '#e05d44'  # Red
    elif percentage < 80:
        color = '#dfb317'  # Yellow
    else:
        color = '#4c1'     # Green (bright green)

    # Format percentage text
    percentage_text = f'{percentage:.1f}%'

    # Calculate SVG dimensions
    # Left side (label) is fixed width, right side (value) scales with text
    left_text = 'OpenAPI Coverage'
    left_width = len(left_text) * 6 + 10  # Approximate width calculation
    right_width = len(percentage_text) * 7 + 10
    total_width = left_width + right_width

    # Simple SVG template
    svg_template = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_width}" height="20" role="img" aria-label="{left_text}: {percentage_text}">
    <title>{left_text}: {percentage_text}</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="{left_width}" height="20" fill="#555"/>
        <rect x="{left_width}" width="{right_width}" height="20" fill="{color}"/>
        <rect width="{total_width}" height="20" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
        <text aria-hidden="true" x="{left_width/2*10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(left_width-10)*10}">{left_text}</text>
        <text x="{left_width/2*10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(left_width-10)*10}">{left_text}</text>
        <text aria-hidden="true" x="{(left_width + right_width/2)*10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(right_width-10)*10}">{percentage_text}</text>
        <text x="{(left_width + right_width/2)*10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(right_width-10)*10}">{percentage_text}</text>
    </g>
</svg>'''

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write badge
    output_path.write_text(svg_template, encoding='utf-8')
    print(f"Badge generated: {output_path}")
