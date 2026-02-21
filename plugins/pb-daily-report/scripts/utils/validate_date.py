#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
날짜 정확성 검증 스크립트
- 어제 날짜와 한국어 요일을 정확히 계산
- JSON 형태로 출력하여 자동화 스크립트에서 사용
"""

from datetime import date, timedelta
import json

def get_yesterday_korean():
    """어제 날짜와 한국어 요일을 정확히 계산"""
    yesterday = date.today() - timedelta(days=1)
    korean_days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    korean_day = korean_days[yesterday.weekday()]

    return {
        'date': yesterday.strftime('%Y-%m-%d'),
        'day': korean_day,
        'title': f"PB Daily Report - {yesterday.strftime('%Y-%m-%d')} ({korean_day})",
        'weekday_index': yesterday.weekday()
    }

def verify_date(year, month, day):
    """특정 날짜의 요일 검증 (디버깅용)"""
    test_date = date(year, month, day)
    korean_days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    korean_day = korean_days[test_date.weekday()]

    return {
        'date': test_date.strftime('%Y-%m-%d'),
        'day': korean_day,
        'weekday_index': test_date.weekday()
    }

if __name__ == "__main__":
    # 기본적으로 어제 날짜 정보 출력
    result = get_yesterday_korean()
    print(json.dumps(result, ensure_ascii=False))

    # 검증 예시 (주석 제거하면 특정 날짜 검증 가능)
    # print(f"\n검증: 2025-09-16 = {verify_date(2025, 9, 16)['day']}")