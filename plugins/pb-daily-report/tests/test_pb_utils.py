"""
pb_utils.py 유닛 테스트
"""

import sys
sys.path.insert(0, '~/.pb-reports')

from pb_utils import (
    extract_date_from_filename,
    get_korean_day_of_week,
    validate_brand,
    is_forbidden_brand,
    format_won_to_millions,
    ALLOWED_BRANDS,
    FORBIDDEN_BRANDS,
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
        # 2026-01-24 is Saturday
        assert get_korean_day_of_week('2026-01-24') == '토요일'

    def test_monday(self):
        # 2026-01-19 is Monday
        assert get_korean_day_of_week('2026-01-19') == '월요일'

    def test_sunday(self):
        # 2026-01-25 is Sunday
        assert get_korean_day_of_week('2026-01-25') == '일요일'


class TestValidateBrand:
    def test_allowed_brand(self):
        assert validate_brand('노어') is True
        assert validate_brand('희애') is True

    def test_forbidden_brand(self):
        assert validate_brand('오드리나') is False

    def test_unknown_brand(self):
        assert validate_brand('테스트브랜드') is False


class TestIsForbiddenBrand:
    def test_forbidden(self):
        assert is_forbidden_brand('오드리나') is True
        assert is_forbidden_brand('로이드') is True

    def test_allowed(self):
        assert is_forbidden_brand('노어') is False


class TestFormatWonToMillions:
    def test_basic(self):
        assert format_won_to_millions(49_700_000) == '49.7'

    def test_round(self):
        assert format_won_to_millions(100_000_000) == '100.0'

    def test_small(self):
        assert format_won_to_millions(500_000) == '0.5'


class TestConstants:
    def test_allowed_brands_count(self):
        assert len(ALLOWED_BRANDS) == 9

    def test_forbidden_brands_count(self):
        assert len(FORBIDDEN_BRANDS) == 6
