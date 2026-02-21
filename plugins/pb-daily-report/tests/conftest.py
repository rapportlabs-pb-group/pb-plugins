"""
pytest 설정 및 공통 fixture
"""

import sys
import pytest

# 테스트에서 사용하는 모듈 경로 추가
sys.path.insert(0, '~/.pb-reports')
sys.path.insert(0, '~/.pb-reports/scripts')


@pytest.fixture
def sample_mcp_raw():
    """샘플 MCP raw JSON 데이터"""
    return {
        'pb_intel_report': {
            'parts': [{
                'text': '{"headline": "테스트 헤드라인", "summary_pb": {"yesterday_performance": {"gmv": "50M", "gmv_growth": "+10%"}}}'
            }]
        },
        'portfolio_stage_briefing': {
            'parts': [{
                'text': '## 포트폴리오 브리핑\n테스트 내용'
            }]
        }
    }


@pytest.fixture
def sample_brand_snapshot_gemini():
    """Gemini 형식 브랜드 스냅샷 데이터"""
    return [
        {'brand': '노어', 'gmv_y_growth': '10M (+5%)', 'spv_y': '1.2'},
        {'brand': '희애', 'gmv_y_growth': '8M (-2%)', 'spv_y': '1.0'},
    ]


@pytest.fixture
def sample_brand_snapshot_legacy():
    """Legacy MCP 형식 브랜드 스냅샷 데이터"""
    return {
        'section_title': '📈 브랜드별 스냅샷',
        'table_data': [
            {'브랜드': '노어', '어제 GMV (등락)': '10M (+5%)', '어제 SPV': '1.2'},
            {'브랜드': '희애', '어제 GMV (등락)': '8M (-2%)', '어제 SPV': '1.0'},
        ]
    }
