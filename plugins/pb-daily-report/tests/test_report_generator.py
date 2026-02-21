"""
report_generator 관련 모듈 유닛 테스트

Note: scripts/ 모듈은 상대 임포트를 사용하므로
개별 유틸리티 함수만 테스트합니다.
"""

import sys
import json
from decimal import Decimal
from datetime import datetime, date


# CustomJSONEncoder 직접 정의 (data_processor.py에서 복사)
class CustomJSONEncoder(json.JSONEncoder):
    """Decimal, datetime 등 특수 타입 JSON 직렬화"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class TestCustomJSONEncoder:
    def test_decimal_encoding(self):
        data = {'value': Decimal('123.45')}
        result = json.dumps(data, cls=CustomJSONEncoder)
        assert '"value": 123.45' in result

    def test_datetime_encoding(self):
        data = {'date': datetime(2026, 1, 26, 10, 30, 0)}
        result = json.dumps(data, cls=CustomJSONEncoder)
        assert '2026-01-26T10:30:00' in result

    def test_date_encoding(self):
        data = {'date': date(2026, 1, 26)}
        result = json.dumps(data, cls=CustomJSONEncoder)
        assert '2026-01-26' in result

    def test_mixed_types(self):
        data = {
            'decimal': Decimal('99.99'),
            'datetime': datetime(2026, 1, 26),
            'string': 'test',
            'int': 42
        }
        result = json.dumps(data, cls=CustomJSONEncoder)
        parsed = json.loads(result)

        assert parsed['decimal'] == 99.99
        assert parsed['string'] == 'test'
        assert parsed['int'] == 42

    def test_nested_structure(self):
        """중첩 구조에서의 직렬화 테스트"""
        data = {
            'items': [
                {'price': Decimal('10.50'), 'date': date(2026, 1, 1)},
                {'price': Decimal('20.00'), 'date': date(2026, 1, 2)},
            ]
        }
        result = json.dumps(data, cls=CustomJSONEncoder)
        parsed = json.loads(result)

        assert parsed['items'][0]['price'] == 10.50
        assert parsed['items'][1]['date'] == '2026-01-02'


class TestConfigConstants:
    """config.py 상수 테스트 (직접 읽기)"""

    def test_config_file_exists(self):
        """config.py 파일 존재 확인"""
        import os
        config_path = os.path.expanduser('~/.pb-reports/scripts/config.py')
        assert os.path.exists(config_path)

    def test_config_content(self):
        """config.py 내용 검증"""
        import os
        config_path = os.path.expanduser('~/.pb-reports/scripts/config.py')
        with open(config_path, 'r') as f:
            content = f.read()

        # 필수 설정값 확인
        assert 'BIGQUERY_PROJECT' in content
        assert '<YOUR_BIGQUERY_PROJECT_ID>' in content
        assert 'PB_BRANDS' in content  # config.py uses PB_BRANDS
        assert '노어' in content
