#!/usr/bin/env python3
"""
MCP Data Date Validator - PB Daily Report MCP 데이터 날짜 검증

MCP 도구에서 반환된 데이터의 날짜가 기대하는 어제 날짜와
일치하는지 검증하여 잘못된 데이터 사용을 방지합니다.
"""

import json
import sys
import re
from datetime import datetime, timedelta, date

def extract_dates_from_mcp_data(mcp_data):
    """MCP 데이터에서 모든 날짜 패턴을 추출"""

    found_dates = []

    # 다양한 날짜 패턴 정의
    date_patterns = [
        # YYYY-MM-DD 형식
        r'(\d{4}-\d{2}-\d{2})',

        # YYYYMMDD 형식
        r'(\d{8})',

        # MM월 DD일 형식
        r'(\d{1,2}월\s*\d{1,2}일)',

        # 어제, 일요일, 월요일 등 텍스트
        r'어제.*?\(([^)]+)\)',
        r'(\d{4}-\d{2}-\d{2})\s*\([^)]+\)',

        # 성과 관련 날짜
        r'(2025-\d{2}-\d{2})',

        # RUN_ID 패턴 (YYYYMMDD-HHMMSS)
        r'(\d{8})-\d{6}',

        # 브리핑 제목의 날짜
        r'브리핑.*?(\d{4}-\d{2}-\d{2})',
        r'Daily Report.*?(\d{4}-\d{2}-\d{2})',
    ]

    for pattern in date_patterns:
        matches = re.findall(pattern, mcp_data, re.IGNORECASE)
        for match in matches:
            # YYYYMMDD를 YYYY-MM-DD로 변환
            if re.match(r'^\d{8}$', match):
                try:
                    formatted_date = f"{match[:4]}-{match[4:6]}-{match[6:8]}"
                    found_dates.append(formatted_date)
                except:
                    pass
            # MM월 DD일을 YYYY-MM-DD로 변환 (올해 기준)
            elif '월' in match and '일' in match:
                try:
                    month_day = re.findall(r'(\d+)월\s*(\d+)일', match)[0]
                    current_year = datetime.now().year
                    formatted_date = f"{current_year}-{int(month_day[0]):02d}-{int(month_day[1]):02d}"
                    found_dates.append(formatted_date)
                except:
                    pass
            else:
                found_dates.append(match)

    return list(set(found_dates))  # 중복 제거

def validate_mcp_date(mcp_data, expected_date, expected_day=None):
    """MCP 데이터의 날짜가 기대값과 일치하는지 검증"""

    found_dates = extract_dates_from_mcp_data(mcp_data)

    # 기대하는 날짜의 다양한 표현 생성
    expected_variations = [
        expected_date,  # 2025-09-22
        expected_date.replace('-', ''),  # 20250922
        datetime.strptime(expected_date, '%Y-%m-%d').strftime('%m월 %d일'),  # 9월 22일
        datetime.strptime(expected_date, '%Y-%m-%d').strftime('%-m월 %-d일'),  # 9월 22일 (macOS)
    ]

    # 요일 검증 (제공된 경우)
    korean_days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    if expected_day:
        expected_weekday = datetime.strptime(expected_date, '%Y-%m-%d').weekday()
        if korean_days[expected_weekday] != expected_day:
            return {
                "valid": False,
                "error": "expected_day_mismatch",
                "message": f"날짜와 요일 불일치: {expected_date}은 {korean_days[expected_weekday]}이지만 {expected_day}로 제공됨",
                "found_dates": found_dates,
                "expected_variations": expected_variations
            }

    # 날짜 매칭 확인
    date_match = False
    for variation in expected_variations:
        if any(variation in str(found_dates) for found_date in found_dates):
            date_match = True
            break

    # 직접 매칭도 확인
    if expected_date in found_dates:
        date_match = True

    if not date_match:
        return {
            "valid": False,
            "error": "date_mismatch",
            "message": f"MCP 데이터 날짜 불일치",
            "expected_date": expected_date,
            "expected_variations": expected_variations,
            "found_dates": found_dates
        }

    # 미래 날짜 체크
    today = date.today().strftime('%Y-%m-%d')
    future_dates = [d for d in found_dates if d > today and re.match(r'^\d{4}-\d{2}-\d{2}$', d)]

    if future_dates:
        return {
            "valid": False,
            "error": "future_date_detected",
            "message": f"미래 날짜 감지됨: {future_dates}",
            "found_dates": found_dates,
            "future_dates": future_dates
        }

    return {
        "valid": True,
        "message": "날짜 검증 성공",
        "expected_date": expected_date,
        "found_dates": found_dates,
        "matched_variations": [v for v in expected_variations if v in str(found_dates)]
    }

def main():
    """메인 실행 함수"""
    if len(sys.argv) < 3:
        print("Usage: python3 mcp_date_validator.py <expected_date> <expected_day> [mcp_data]")
        print("Example: python3 mcp_date_validator.py 2025-09-22 월요일")
        sys.exit(1)

    expected_date = sys.argv[1]
    expected_day = sys.argv[2] if len(sys.argv) > 2 else None

    # MCP 데이터는 stdin 또는 세 번째 인자로 받음
    if len(sys.argv) > 3:
        mcp_data = sys.argv[3]
    else:
        mcp_data = sys.stdin.read()

    try:
        # JSON 형태인 경우 파싱
        if mcp_data.strip().startswith('{'):
            data = json.loads(mcp_data)
            # daily_intelligence_briefing_report 섹션 찾기
            if 'daily_intelligence_briefing_report' in data:
                mcp_data = data['daily_intelligence_briefing_report']
            elif 'report' in data:
                mcp_data = data['report']
            elif 'result' in data:
                mcp_data = str(data['result'])
            else:
                mcp_data = str(data)
    except json.JSONDecodeError:
        # JSON이 아닌 경우 원본 텍스트 사용
        pass

    result = validate_mcp_date(mcp_data, expected_date, expected_day)

    # 결과 출력
    if result["valid"]:
        print("✅ PASS: MCP 데이터 날짜 검증 성공")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    else:
        print("❌ FAIL: MCP 데이터 날짜 검증 실패")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(15)

if __name__ == "__main__":
    main()