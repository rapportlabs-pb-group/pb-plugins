#!/usr/bin/env python3
"""
Enhanced Date Validator - PB Daily Report 날짜 정확성 강화

기존 validate_date.py를 확장하여 더 엄격한 날짜 검증과
중복 확인을 위한 추가 정보를 제공합니다.
"""

import json
from datetime import date, timedelta

def get_yesterday_with_validation():
    """어제 날짜를 계산하고 검증을 위한 추가 정보 제공"""

    yesterday = date.today() - timedelta(days=1)
    today = date.today()

    korean_days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    korean_day = korean_days[yesterday.weekday()]

    return {
        # 기본 날짜 정보
        'date': yesterday.strftime('%Y-%m-%d'),
        'date_numeric': yesterday.strftime('%Y%m%d'),
        'day': korean_day,
        'weekday_index': yesterday.weekday(),

        # 제목 및 검색용
        'title': f"PB Daily Report - {yesterday.strftime('%Y-%m-%d')} ({korean_day})",
        'search_query': f"PB Daily Report {yesterday.strftime('%Y-%m-%d')}",
        'search_query_alt': f"PB Daily Report - {yesterday.strftime('%Y-%m-%d')}",

        # 검증용 정보
        'validation_timestamp': today.isoformat(),
        'expected_date_formats': [
            yesterday.strftime('%Y-%m-%d'),
            yesterday.strftime('%Y%m%d'),
            yesterday.strftime('%m월 %d일'),
            f"{yesterday.month}월 {yesterday.day}일"
        ],

        # 비교용 (주말/평일 체크)
        'is_weekend': yesterday.weekday() >= 5,
        'is_monday': yesterday.weekday() == 0,

        # 디버깅용
        'today': today.strftime('%Y-%m-%d'),
        'days_since_epoch': (yesterday - date(1970, 1, 1)).days
    }

def validate_date_string(date_str, expected_date):
    """주어진 날짜 문자열이 예상 날짜와 일치하는지 검증"""

    try:
        # 다양한 형식으로 파싱 시도
        formats = [
            '%Y-%m-%d',
            '%Y%m%d',
            '%Y/%m/%d',
            '%m/%d/%Y'
        ]

        for fmt in formats:
            try:
                parsed_date = date.strptime(date_str, fmt).date()
                return parsed_date.strftime('%Y-%m-%d') == expected_date
            except ValueError:
                continue

        return False

    except Exception:
        return False

def main():
    """메인 실행 함수"""
    result = get_yesterday_with_validation()
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()