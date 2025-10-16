"""Unit tests for coverage.py markdown helper functions.

Tests the markdown generation helpers extracted during Phase 1 of the
Coverage Consolidation Plan. These helpers format coverage data as
markdown tables with emoji indicators.
"""

import pytest
from scripts.swagger_sync.coverage import (
    _format_rate_emoji,
    _build_coverage_summary_markdown,
    _build_automation_coverage_markdown,
    _build_quality_metrics_markdown,
    _build_method_breakdown_markdown,
    _build_tag_coverage_markdown,
    _build_top_files_markdown,
    _build_orphaned_warnings_markdown,
)


class TestFormatRateEmoji:
    """Tests for _format_rate_emoji helper."""

    def test_green_emoji_90_percent(self):
        """Should use green emoji for 90%+ coverage."""
        result = _format_rate_emoji(9, 10, 0.9)
        assert '🟢' in result
        assert '9/10' in result
        assert '90.0%' in result

    def test_green_emoji_100_percent(self):
        """Should use green emoji for 100% coverage."""
        result = _format_rate_emoji(15, 15, 1.0)
        assert '🟢' in result
        assert '15/15' in result
        assert '100.0%' in result

    def test_yellow_emoji_60_percent(self):
        """Should use yellow emoji for 60-89% coverage."""
        result = _format_rate_emoji(6, 10, 0.6)
        assert '🟡' in result
        assert '6/10' in result
        assert '60.0%' in result

    def test_yellow_emoji_89_percent(self):
        """Should use yellow emoji for upper bound of yellow range."""
        result = _format_rate_emoji(89, 100, 0.89)
        assert '🟡' in result
        assert '89/100' in result
        assert '89.0%' in result

    def test_red_emoji_below_60_percent(self):
        """Should use red emoji for <60% coverage."""
        result = _format_rate_emoji(5, 10, 0.5)
        assert '🔴' in result
        assert '5/10' in result
        assert '50.0%' in result

    def test_red_emoji_zero_percent(self):
        """Should use red emoji for 0% coverage."""
        result = _format_rate_emoji(0, 10, 0.0)
        assert '🔴' in result
        assert '0/10' in result
        assert '0.0%' in result

    def test_format_structure(self):
        """Should format as 'emoji count/total (rate%)'."""
        result = _format_rate_emoji(7, 10, 0.7)
        # Should match pattern: emoji space count/total space (percent%)
        assert result.count('/') == 1
        assert result.count('(') == 1
        assert result.count(')') == 1
        assert result.endswith('%)')


class TestBuildCoverageSummaryMarkdown:
    """Tests for _build_coverage_summary_markdown helper."""

    def test_section_header(self):
        """Should include section header with emoji."""
        summary = self._minimal_summary()
        lines = _build_coverage_summary_markdown(summary)
        assert '## 📊 Coverage Summary' in lines

    def test_table_structure(self):
        """Should include markdown table with headers and separator."""
        summary = self._minimal_summary()
        lines = _build_coverage_summary_markdown(summary)
        assert any('| Metric | Value | Coverage |' in line for line in lines)
        assert any('|--------|-------|----------|' in line for line in lines)

    def test_handlers_total_row(self):
        """Should include handlers considered count."""
        summary = self._minimal_summary()
        summary['handlers_total'] = 42
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Handlers considered' in line_str
        assert '42' in line_str

    def test_ignored_handlers_row(self):
        """Should include ignored handlers count."""
        summary = self._minimal_summary()
        summary['ignored_total'] = 59
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Ignored handlers' in line_str
        assert '59' in line_str

    def test_with_openapi_block_includes_emoji(self):
        """Should include emoji for openapi block coverage."""
        summary = self._minimal_summary()
        summary['with_openapi_block'] = 15
        summary['handlers_total'] = 15
        summary['coverage_rate_handlers_with_block'] = 1.0
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'With OpenAPI block' in line_str
        assert '🟢' in line_str  # 100% should be green

    def test_in_swagger_includes_emoji(self):
        """Should include emoji for swagger coverage."""
        summary = self._minimal_summary()
        summary['handlers_in_swagger'] = 10
        summary['handlers_total'] = 20
        summary['coverage_rate_handlers_in_swagger'] = 0.5
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'In swagger' in line_str
        assert '🔴' in line_str  # 50% should be red

    def test_definition_matches_includes_emoji(self):
        """Should include emoji for definition match rate."""
        summary = self._minimal_summary()
        summary['definition_matches'] = 8
        summary['with_openapi_block'] = 10
        summary['operation_definition_match_rate'] = 0.8
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Definition matches' in line_str
        assert '🟡' in line_str  # 80% should be yellow

    def test_swagger_only_operations_row(self):
        """Should include swagger only operations count."""
        summary = self._minimal_summary()
        summary['swagger_only_operations'] = 3
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Swagger only operations' in line_str
        assert '3' in line_str

    def test_model_components_generated_when_present(self):
        """Should include model components generated row when key is present."""
        summary = self._minimal_summary()
        summary['model_components_generated'] = 36
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Model components generated' in line_str
        assert '36' in line_str

    def test_model_components_not_generated_when_absent(self):
        """Should not include model components row when key is absent."""
        summary = self._minimal_summary()
        # Explicitly exclude model_components_generated
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Model components generated' not in line_str

    def test_schemas_not_generated_when_present(self):
        """Should include schemas not generated row when key is present."""
        summary = self._minimal_summary()
        summary['model_components_existing_not_generated'] = 5
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Schemas not generated' in line_str
        assert '5' in line_str

    def test_schemas_not_generated_when_absent(self):
        """Should not include schemas not generated row when key is absent."""
        summary = self._minimal_summary()
        # Explicitly exclude model_components_existing_not_generated
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Schemas not generated' not in line_str

    def test_both_model_metrics_present(self):
        """Should include both model component metrics when both keys are present."""
        summary = self._minimal_summary()
        summary['model_components_generated'] = 36
        summary['model_components_existing_not_generated'] = 0
        lines = _build_coverage_summary_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Model components generated' in line_str
        assert 'Schemas not generated' in line_str
        assert '36' in line_str
        # Check that table structure is maintained (proper number of pipe characters per row)
        table_rows = [line for line in lines if line.startswith('|')]
        for row in table_rows:
            # Each row should have 4 pipes (3 columns + start/end)
            assert row.count('|') == 4, f"Row has wrong number of pipes: {row}"

    @staticmethod
    def _minimal_summary():
        """Create minimal valid summary dict."""
        return {
            'handlers_total': 15,
            'ignored_total': 0,
            'with_openapi_block': 15,
            'handlers_in_swagger': 15,
            'definition_matches': 15,
            'swagger_only_operations': 0,
            'coverage_rate_handlers_with_block': 1.0,
            'coverage_rate_handlers_in_swagger': 1.0,
            'operation_definition_match_rate': 1.0,
        }


class TestBuildAutomationCoverageMarkdown:
    """Tests for _build_automation_coverage_markdown helper."""

    def test_section_header(self):
        """Should include section header with emoji."""
        summary = self._minimal_summary()
        lines = _build_automation_coverage_markdown(summary)
        assert '## 🤖 Automation Coverage (Technical Debt)' in lines

    def test_table_structure(self):
        """Should include markdown table with headers."""
        summary = self._minimal_summary()
        lines = _build_automation_coverage_markdown(summary)
        assert any('| Item Type | Count | Automation Rate |' in line for line in lines)

    def test_components_automated_row(self):
        """Should show automated components count with emoji."""
        summary = self._minimal_summary()
        summary['automated_components'] = 36
        summary['total_swagger_components'] = 36
        summary['component_automation_rate'] = 1.0
        lines = _build_automation_coverage_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Components (automated)' in line_str
        assert '36' in line_str
        assert '🟢' in line_str  # 100% automation should be green

    def test_components_orphaned_row(self):
        """Should show orphaned components count."""
        summary = self._minimal_summary()
        summary['orphaned_components_count'] = 5
        lines = _build_automation_coverage_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Components (manual/orphan)' in line_str
        assert '5' in line_str
        assert 'TECHNICAL DEBT' in line_str

    def test_endpoints_automated_row(self):
        """Should show automated endpoints count with emoji."""
        summary = self._minimal_summary()
        summary['automated_endpoints'] = 15
        summary['total_swagger_endpoints'] = 15
        summary['endpoint_automation_rate'] = 1.0
        lines = _build_automation_coverage_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Endpoints (automated)' in line_str
        assert '15' in line_str
        assert '🟢' in line_str

    def test_endpoints_orphaned_row(self):
        """Should show orphaned endpoints count."""
        summary = self._minimal_summary()
        summary['orphaned_endpoints_count'] = 2
        lines = _build_automation_coverage_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Endpoints (manual/orphan)' in line_str
        assert '2' in line_str
        assert 'TECHNICAL DEBT' in line_str

    def test_overall_automation_row(self):
        """Should show overall automation in bold."""
        summary = self._minimal_summary()
        summary['total_items'] = 51
        summary['total_orphans'] = 0
        summary['automation_coverage_rate'] = 1.0
        lines = _build_automation_coverage_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'OVERALL AUTOMATION' in line_str
        assert '**51**' in line_str or '51' in line_str

    def test_total_orphans_row(self):
        """Should show total orphans in bold."""
        summary = self._minimal_summary()
        summary['total_orphans'] = 7
        lines = _build_automation_coverage_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'Total orphans (debt)' in line_str
        assert '**7**' in line_str or '7' in line_str
        assert 'NEEDS ATTENTION' in line_str

    @staticmethod
    def _minimal_summary():
        """Create minimal valid summary dict."""
        return {
            'automated_components': 36,
            'total_swagger_components': 36,
            'orphaned_components_count': 0,
            'component_automation_rate': 1.0,
            'automated_endpoints': 15,
            'total_swagger_endpoints': 15,
            'orphaned_endpoints_count': 0,
            'endpoint_automation_rate': 1.0,
            'total_items': 51,
            'total_orphans': 0,
            'automation_coverage_rate': 1.0,
        }


class TestBuildQualityMetricsMarkdown:
    """Tests for _build_quality_metrics_markdown helper."""

    def test_section_header(self):
        """Should include section header with emoji."""
        summary = self._minimal_summary()
        lines = _build_quality_metrics_markdown(summary)
        assert '## ✨ Documentation Quality Metrics' in lines

    def test_table_structure(self):
        """Should include markdown table with headers."""
        summary = self._minimal_summary()
        lines = _build_quality_metrics_markdown(summary)
        assert any('| Quality Indicator | Count | Rate |' in line for line in lines)

    def test_summary_row(self):
        """Should include summary quality row with emoji."""
        summary = self._minimal_summary()
        summary['endpoints_with_summary'] = 10
        summary['with_openapi_block'] = 10
        summary['quality_rate_summary'] = 1.0
        lines = _build_quality_metrics_markdown(summary)
        line_str = '\n'.join(lines)
        assert '📝 Summary' in line_str
        assert '10' in line_str
        assert '🟢' in line_str

    def test_description_row(self):
        """Should include description quality row."""
        summary = self._minimal_summary()
        lines = _build_quality_metrics_markdown(summary)
        line_str = '\n'.join(lines)
        assert '📄 Description' in line_str

    def test_parameters_row(self):
        """Should include parameters quality row."""
        summary = self._minimal_summary()
        lines = _build_quality_metrics_markdown(summary)
        line_str = '\n'.join(lines)
        assert '🔧 Parameters' in line_str

    def test_request_body_row(self):
        """Should include request body quality row."""
        summary = self._minimal_summary()
        lines = _build_quality_metrics_markdown(summary)
        line_str = '\n'.join(lines)
        assert '📦 Request body' in line_str

    def test_multiple_responses_row(self):
        """Should include multiple responses quality row."""
        summary = self._minimal_summary()
        lines = _build_quality_metrics_markdown(summary)
        line_str = '\n'.join(lines)
        assert '🔀 Multiple responses' in line_str

    def test_examples_row(self):
        """Should include examples quality row."""
        summary = self._minimal_summary()
        lines = _build_quality_metrics_markdown(summary)
        line_str = '\n'.join(lines)
        assert '💡 Examples' in line_str

    @staticmethod
    def _minimal_summary():
        """Create minimal valid summary dict."""
        return {
            'with_openapi_block': 15,
            'endpoints_with_summary': 15,
            'endpoints_with_description': 12,
            'endpoints_with_parameters': 10,
            'endpoints_with_request_body': 5,
            'endpoints_with_multiple_responses': 8,
            'endpoints_with_examples': 3,
            'quality_rate_summary': 1.0,
            'quality_rate_description': 0.8,
            'quality_rate_parameters': 0.67,
            'quality_rate_request_body': 0.33,
            'quality_rate_multiple_responses': 0.53,
            'quality_rate_examples': 0.2,
        }


class TestBuildMethodBreakdownMarkdown:
    """Tests for _build_method_breakdown_markdown helper."""

    def test_section_header(self):
        """Should include section header with emoji."""
        summary = self._minimal_summary()
        lines = _build_method_breakdown_markdown(summary)
        assert '## 🔄 HTTP Method Breakdown' in lines

    def test_table_structure(self):
        """Should include markdown table with headers."""
        summary = self._minimal_summary()
        lines = _build_method_breakdown_markdown(summary)
        assert any('| Method | Total | Documented | In Swagger |' in line for line in lines)

    def test_get_method_with_emoji(self):
        """Should include GET method with book emoji."""
        summary = self._minimal_summary()
        lines = _build_method_breakdown_markdown(summary)
        line_str = '\n'.join(lines)
        assert '📖 GET' in line_str

    def test_post_method_with_emoji(self):
        """Should include POST method with inbox emoji."""
        summary = {
            'method_statistics': {
                'POST': {'total': 5, 'documented': 5, 'in_swagger': 5}
            }
        }
        lines = _build_method_breakdown_markdown(summary)
        line_str = '\n'.join(lines)
        assert '📥 POST' in line_str

    def test_put_method_with_emoji(self):
        """Should include PUT method with outbox emoji."""
        summary = {
            'method_statistics': {
                'PUT': {'total': 3, 'documented': 2, 'in_swagger': 2}
            }
        }
        lines = _build_method_breakdown_markdown(summary)
        line_str = '\n'.join(lines)
        assert '📤 PUT' in line_str

    def test_delete_method_with_emoji(self):
        """Should include DELETE method with trash emoji."""
        summary = {
            'method_statistics': {
                'DELETE': {'total': 2, 'documented': 1, 'in_swagger': 1}
            }
        }
        lines = _build_method_breakdown_markdown(summary)
        line_str = '\n'.join(lines)
        assert '🗑️ DELETE' in line_str

    def test_documented_rate_with_emoji(self):
        """Should include emoji based on documentation rate."""
        summary = {
            'method_statistics': {
                'GET': {'total': 10, 'documented': 5, 'in_swagger': 5}
            }
        }
        lines = _build_method_breakdown_markdown(summary)
        line_str = '\n'.join(lines)
        assert '🔴' in line_str  # 50% should be red

    @staticmethod
    def _minimal_summary():
        """Create minimal valid summary dict."""
        return {
            'method_statistics': {
                'GET': {'total': 10, 'documented': 10, 'in_swagger': 10}
            }
        }


class TestBuildTagCoverageMarkdown:
    """Tests for _build_tag_coverage_markdown helper."""

    def test_empty_tags_returns_empty_list(self):
        """Should return empty list when no tags present."""
        summary = {'tag_coverage': {}, 'unique_tags': 0}
        lines = _build_tag_coverage_markdown(summary)
        assert lines == []

    def test_section_header_with_unique_count(self):
        """Should include section header with unique tag count."""
        summary = self._minimal_summary()
        lines = _build_tag_coverage_markdown(summary)
        assert any('🏷️ Tag Coverage' in line for line in lines)
        assert any('Unique tags: 2' in line for line in lines)

    def test_table_structure(self):
        """Should include markdown table with headers."""
        summary = self._minimal_summary()
        lines = _build_tag_coverage_markdown(summary)
        assert any('| Tag | Endpoints |' in line for line in lines)

    def test_tag_rows_sorted(self):
        """Should list tags in alphabetical order."""
        summary = {
            'tag_coverage': {'zebra': 1, 'alpha': 5, 'beta': 3},
            'unique_tags': 3
        }
        lines = _build_tag_coverage_markdown(summary)
        line_str = '\n'.join(lines)
        # Find positions of tags in the output
        alpha_pos = line_str.find('alpha')
        beta_pos = line_str.find('beta')
        zebra_pos = line_str.find('zebra')
        assert alpha_pos < beta_pos < zebra_pos

    def test_tag_endpoint_counts(self):
        """Should show correct endpoint count for each tag."""
        summary = self._minimal_summary()
        lines = _build_tag_coverage_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'roles' in line_str
        assert '8' in line_str
        assert 'users' in line_str
        assert '5' in line_str

    @staticmethod
    def _minimal_summary():
        """Create minimal valid summary dict."""
        return {
            'tag_coverage': {'roles': 8, 'users': 5},
            'unique_tags': 2
        }


class TestBuildTopFilesMarkdown:
    """Tests for _build_top_files_markdown helper."""

    def test_section_header(self):
        """Should include section header with emoji."""
        summary = self._minimal_summary()
        lines = _build_top_files_markdown(summary)
        assert '## 📁 Top Files by Endpoint Count' in lines

    def test_table_structure(self):
        """Should include markdown table with headers."""
        summary = self._minimal_summary()
        lines = _build_top_files_markdown(summary)
        assert any('| File | Total | Documented |' in line for line in lines)

    def test_limits_to_top_10(self):
        """Should only show top 10 files."""
        summary = {
            'file_statistics': {
                f'file{i}.py': {'total': 20 - i, 'documented': 20 - i}
                for i in range(15)  # 15 files
            }
        }
        lines = _build_top_files_markdown(summary)
        # Should have header + separator + 10 data rows
        # Count lines that look like data rows (start with |)
        data_lines = [l for l in lines if l.startswith('|') and 'File' not in l and '----' not in l]
        assert len(data_lines) == 10

    def test_sorted_by_total_descending(self):
        """Should list files by total endpoint count (highest first)."""
        summary = {
            'file_statistics': {
                'low.py': {'total': 2, 'documented': 2},
                'high.py': {'total': 20, 'documented': 20},
                'mid.py': {'total': 10, 'documented': 10},
            }
        }
        lines = _build_top_files_markdown(summary)
        line_str = '\n'.join(lines)
        # Find positions in output
        high_pos = line_str.find('high.py')
        mid_pos = line_str.find('mid.py')
        low_pos = line_str.find('low.py')
        assert high_pos < mid_pos < low_pos

    def test_shows_basename_only(self):
        """Should show only filename, not full path."""
        summary = {
            'file_statistics': {
                '/full/path/to/handler.py': {'total': 5, 'documented': 5}
            }
        }
        lines = _build_top_files_markdown(summary)
        line_str = '\n'.join(lines)
        assert 'handler.py' in line_str
        assert '/full/path/to/' not in line_str

    def test_documented_rate_with_emoji(self):
        """Should include emoji based on documentation rate."""
        summary = {
            'file_statistics': {
                'handler.py': {'total': 10, 'documented': 9}
            }
        }
        lines = _build_top_files_markdown(summary)
        line_str = '\n'.join(lines)
        assert '🟢' in line_str  # 90% should be green

    @staticmethod
    def _minimal_summary():
        """Create minimal valid summary dict."""
        return {
            'file_statistics': {
                'roles_handler.py': {'total': 8, 'documented': 8},
                'users_handler.py': {'total': 5, 'documented': 4},
            }
        }


class TestBuildOrphanedWarningsMarkdown:
    """Tests for _build_orphaned_warnings_markdown helper."""

    def test_empty_orphans_returns_empty_list(self):
        """Should return empty list when no orphans."""
        lines = _build_orphaned_warnings_markdown([], [])
        assert lines == []

    def test_orphaned_components_section(self):
        """Should include orphaned components section."""
        orphaned_comps = ['UserProfile', 'ServerConfig']
        lines = _build_orphaned_warnings_markdown(orphaned_comps, [])
        line_str = '\n'.join(lines)
        assert '## 🚨 Orphaned Components (no @openapi.component)' in line_str
        assert 'UserProfile' in line_str
        assert 'ServerConfig' in line_str

    def test_orphaned_components_sorted(self):
        """Should list orphaned components alphabetically."""
        orphaned_comps = ['Zebra', 'Alpha', 'Beta']
        lines = _build_orphaned_warnings_markdown(orphaned_comps, [])
        line_str = '\n'.join(lines)
        alpha_pos = line_str.find('Alpha')
        beta_pos = line_str.find('Beta')
        zebra_pos = line_str.find('Zebra')
        assert alpha_pos < beta_pos < zebra_pos

    def test_orphaned_components_backticked(self):
        """Should wrap component names in backticks."""
        orphaned_comps = ['UserProfile']
        lines = _build_orphaned_warnings_markdown(orphaned_comps, [])
        line_str = '\n'.join(lines)
        assert '`UserProfile`' in line_str

    def test_orphaned_endpoints_section(self):
        """Should include orphaned endpoints section."""
        swagger_only = [
            {'path': '/api/v1/test', 'method': 'get'},
            {'path': '/api/v1/other', 'method': 'post'},
        ]
        lines = _build_orphaned_warnings_markdown([], swagger_only)
        line_str = '\n'.join(lines)
        assert '## 🚨 Orphaned Endpoints (no Python decorator)' in line_str
        assert 'GET /api/v1/test' in line_str
        assert 'POST /api/v1/other' in line_str

    def test_orphaned_endpoints_sorted(self):
        """Should list orphaned endpoints sorted by path then method."""
        swagger_only = [
            {'path': '/z', 'method': 'get'},
            {'path': '/a', 'method': 'post'},
            {'path': '/a', 'method': 'get'},
        ]
        lines = _build_orphaned_warnings_markdown([], swagger_only)
        line_str = '\n'.join(lines)
        # /a/get should come before /a/post should come before /z/get
        a_get_pos = line_str.find('GET /a')
        a_post_pos = line_str.find('POST /a')
        z_get_pos = line_str.find('GET /z')
        assert a_get_pos < a_post_pos < z_get_pos

    def test_orphaned_endpoints_backticked(self):
        """Should wrap endpoint paths in backticks."""
        swagger_only = [{'path': '/api/v1/test', 'method': 'get'}]
        lines = _build_orphaned_warnings_markdown([], swagger_only)
        line_str = '\n'.join(lines)
        assert '`GET /api/v1/test`' in line_str

    def test_orphaned_endpoints_truncated_at_25(self):
        """Should truncate to 25 endpoints and show count."""
        swagger_only = [
            {'path': f'/api/v1/endpoint{i}', 'method': 'get'}
            for i in range(30)
        ]
        lines = _build_orphaned_warnings_markdown([], swagger_only)
        line_str = '\n'.join(lines)
        # Should show "... and 5 more"
        assert '... and 5 more' in line_str

    def test_orphaned_endpoints_method_uppercase(self):
        """Should uppercase HTTP method in output."""
        swagger_only = [{'path': '/test', 'method': 'get'}]
        lines = _build_orphaned_warnings_markdown([], swagger_only)
        line_str = '\n'.join(lines)
        assert 'GET /test' in line_str
        assert 'get /test' not in line_str

    def test_both_sections_when_both_present(self):
        """Should include both sections when both have orphans."""
        orphaned_comps = ['UserProfile']
        swagger_only = [{'path': '/test', 'method': 'get'}]
        lines = _build_orphaned_warnings_markdown(orphaned_comps, swagger_only)
        line_str = '\n'.join(lines)
        assert '## 🚨 Orphaned Components' in line_str
        assert '## 🚨 Orphaned Endpoints' in line_str
        assert 'UserProfile' in line_str
        assert 'GET /test' in line_str
