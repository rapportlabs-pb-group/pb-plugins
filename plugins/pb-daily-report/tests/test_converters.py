"""
converters 모듈 유닛 테스트
"""

import sys
sys.path.insert(0, '~/.pb-reports')

from converters import (
    extract_date_from_filename,
    get_korean_day_of_week,
    create_notion_table,
    parse_pb_intel_report,
    convert_summary_section,
    convert_brand_snapshot_section,
    convert_top_performers_section,
    convert_urgent_priorities_section,
    convert_action_items_section,
)


class TestExtractDateFromFilename:
    def test_valid_filename(self):
        assert extract_date_from_filename('mcp-raw-2026-01-24.json') == '2026-01-24'

    def test_path_with_date(self):
        assert extract_date_from_filename('/path/to/mcp-raw-2026-01-24.json') == '2026-01-24'

    def test_no_date(self):
        assert extract_date_from_filename('mcp-raw.json') is None


class TestGetKoreanDayOfWeek:
    def test_saturday(self):
        assert get_korean_day_of_week('2026-01-24') == '토요일'

    def test_monday(self):
        assert get_korean_day_of_week('2026-01-26') == '월요일'

    def test_sunday(self):
        assert get_korean_day_of_week('2026-01-25') == '일요일'


class TestCreateNotionTable:
    def test_basic_table(self):
        headers = ['이름', '값']
        rows = [['A', '1'], ['B', '2']]
        result = create_notion_table(headers, rows)

        assert '<table>' in result
        assert '</table>' in result
        assert '<td>이름</td>' in result
        assert '<td>A</td>' in result

    def test_with_alignments(self):
        headers = ['이름', '값']
        rows = [['A', '1']]
        alignments = [':---', ':---:']
        result = create_notion_table(headers, rows, alignments)

        assert '<td>:---</td>' in result
        assert '<td>:---:</td>' in result


class TestParsePbIntelReport:
    def test_direct_json(self):
        text = '{"headline": "테스트 헤드라인"}'
        result = parse_pb_intel_report(text)
        assert result['headline'] == '테스트 헤드라인'

    def test_json_with_code_fence(self):
        text = '```json\n{"headline": "테스트"}\n```'
        result = parse_pb_intel_report(text)
        assert result['headline'] == '테스트'

    def test_nested_structure(self):
        text = '{"daily_intelligence_briefing": {"headline": "중첩 테스트"}}'
        result = parse_pb_intel_report(text)
        assert result['headline'] == '중첩 테스트'

    def test_key_normalization(self):
        text = '{"overall_summary": {"data": "test"}, "todays_action_items": []}'
        result = parse_pb_intel_report(text)
        assert 'summary_pb' in result
        assert 'action_items' in result


class TestConvertSummarySection:
    def test_basic(self):
        data = {
            'section_title': '📊 전체 PB 요약',
            'yesterday_performance': {
                'gmv': '50,000,000',
                'gmv_growth': '+10%',
                'spv': '1.5',
                'spv_growth': '+5%'
            }
        }
        result = convert_summary_section(data)

        assert '## 📊 전체 PB 요약' in result
        assert '50,000,000원' in result
        assert '+10%' in result


class TestConvertBrandSnapshotSection:
    def test_list_format(self):
        """Gemini 출력 형식 (list) 테스트"""
        data = [
            {'brand': '노어', 'gmv_y_growth': '10M (+5%)'},
            {'brand': '희애', 'gmv_y_growth': '8M (-2%)'}
        ]
        result = convert_brand_snapshot_section(data)

        assert '브랜드별 스냅샷' in result
        assert '<table>' in result
        assert '노어' in result
        assert '희애' in result

    def test_dict_format(self):
        """Legacy MCP 출력 형식 (dict) 테스트"""
        data = {
            'section_title': '📈 브랜드별 스냅샷',
            'table_data': [
                {'브랜드': '노어', '어제 GMV (등락)': '10M (+5%)'}
            ]
        }
        result = convert_brand_snapshot_section(data)

        assert '## 📈 브랜드별 스냅샷' in result
        assert '노어' in result


class TestConvertTopPerformersSection:
    def test_list_format(self):
        """Gemini 출력 형식 (list) 테스트"""
        data = [
            {'type': '🏆 MVP', 'name': '노어', 'metrics': 'GMV 50M', 'diagnosis': '좋음'}
        ]
        result = convert_top_performers_section(data)

        assert '🏆 MVP: 노어' in result
        assert 'GMV 50M' in result
        assert '좋음' in result

    def test_dict_format_mvp_keys(self):
        """Legacy mvp_1, mvp_2 형식 테스트"""
        data = {
            'mvp_1': {'brand_name': '노어', 'gmv_y': '50M', 'gmv_growth': '10', 'diagnosis': '우수'}
        }
        result = convert_top_performers_section(data)

        assert 'MVP: 노어' in result
        assert '우수' in result


class TestConvertUrgentPrioritiesSection:
    def test_list_format(self):
        """Gemini 출력 형식 (list) 테스트"""
        data = [
            {'type': '❗️성과 하락', 'name': '브랜드A', 'diagnosis': '점검 필요'}
        ]
        result = convert_urgent_priorities_section(data)

        assert '❗️성과 하락: 브랜드A' in result
        assert '점검 필요' in result


class TestConvertActionItemsSection:
    def test_list_format(self):
        """새 MCP 구조 (list) 테스트"""
        data = [
            {'category': '긴급', 'target': '노어', 'instruction': '재고 확인'}
        ]
        result = convert_action_items_section(data)

        assert "Today's Action Items" in result
        assert '[긴급]' in result
        assert '노어' in result

    def test_dict_format(self):
        """기존 구조 (dict) 테스트"""
        data = {
            'section_title': "🎯 Today's Action Items",
            'items': ['액션 1', '액션 2']
        }
        result = convert_action_items_section(data)

        assert '액션 1' in result
        assert '액션 2' in result
