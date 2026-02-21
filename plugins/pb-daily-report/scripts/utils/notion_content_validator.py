#!/usr/bin/env python3
"""
Notion Content Validator - PB Daily Report 완전성 검증

MCP에서 생성된 원본 데이터와 Notion 페이지 내용을 비교하여
모든 필수 섹션이 포함되었는지 검증합니다.

v2.0 개선사항:
- 날짜 일치성 검증 추가
- 브랜드 데이터 완전성 체크 강화
- Top 10 상품 리스트 포함 여부 확인
"""

import json
import sys
import re
from datetime import datetime, date
from typing import Dict, List, Set

def extract_mcp_sections(mcp_data: str) -> Set[str]:
    """MCP 원본 데이터에서 포함된 섹션들을 추출"""
    sections = set()

    # JSON 파싱
    try:
        data = json.loads(mcp_data)
        report_content = data.get("daily_intelligence_briefing_report", "")
    except:
        print("ERROR: MCP 데이터 JSON 파싱 실패")
        sys.exit(10)

    # 필수 섹션 패턴 검사
    section_patterns = {
        "brand_snapshots": r"📈 브랜드별 스냅샷|브랜드별.*스냅샷",
        "top_performers": r"🚀 Top Performers|Top Performers",
        "urgent_priorities": r"🚨 Urgent Priorities|Urgent Priorities",
        "action_items": r"🎯.*Action Items|Today's Action Items",
        "top_10_products": r"🔥 Top 10.*상품|Top 10.*급성장",
        "missed_opportunities": r"💡 Missed Opportunities|Missed Opportunities",
        "required_actions": r"⚠️.*조치가 필요한|조치가 필요한 상품",
        "detailed_analysis": r"📊 상품별 상세.*분석|상품별.*상세.*분석"
    }

    for section_key, pattern in section_patterns.items():
        if re.search(pattern, report_content, re.IGNORECASE):
            sections.add(section_key)

    # 브랜드 개수 확인 (최소 8개 브랜드 포함되어야 함)
    brand_patterns = [
        r"노어.*GMV", r"다나앤페타.*GMV", r"마치마라.*GMV",
        r"브에트와.*GMV", r"아르앙.*GMV", r"지재.*GMV",
        r"희애.*GMV", r"퀸즈셀렉션.*GMV"
    ]
    brand_count = sum(1 for pattern in brand_patterns
                     if re.search(pattern, report_content))

    if brand_count >= 7:  # 최소 7개 브랜드 (퀸즈셀렉션 제외 가능)
        sections.add("sufficient_brands")

    return sections

def extract_notion_sections(notion_content: str) -> Set[str]:
    """Notion 페이지 내용에서 포함된 섹션들을 추출"""
    sections = set()

    # 필수 섹션 패턴 검사 (Notion 마크다운 형식)
    section_patterns = {
        "brand_snapshots": r"브랜드별.*스냅샷|📈.*브랜드별",
        "top_performers": r"🚀.*Top Performers|Top Performers",
        "urgent_priorities": r"🚨.*Urgent Priorities|Urgent Priorities",
        "action_items": r"🎯.*Action Items|Today's Action Items",
        "top_10_products": r"🔥.*Top 10.*상품|Top 10.*급성장",
        "missed_opportunities": r"💡.*Missed Opportunities|Missed Opportunities",
        "required_actions": r"⚠️.*조치가 필요한|조치가 필요한 상품",
        "detailed_analysis": r"📊.*상품별 상세.*분석|상품별.*상세.*분석"
    }

    for section_key, pattern in section_patterns.items():
        if re.search(pattern, notion_content, re.IGNORECASE):
            sections.add(section_key)

    # 브랜드 개수 확인
    brand_patterns = [
        r"\*\*노어\*\*", r"\*\*다나앤페타\*\*", r"\*\*마치마라\*\*",
        r"\*\*브에트와\*\*", r"\*\*아르앙\*\*", r"\*\*지재\*\*",
        r"\*\*희애\*\*", r"\*\*퀸즈셀렉션\*\*"
    ]
    brand_count = sum(1 for pattern in brand_patterns
                     if re.search(pattern, notion_content))

    if brand_count >= 7:
        sections.add("sufficient_brands")

    return sections

def extract_date_from_content(content: str) -> List[str]:
    """컨텐츠에서 날짜 정보 추출"""
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        r'(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)',  # YYYY년 MM월 DD일
        r'(\d{1,2}월\s*\d{1,2}일)',  # MM월 DD일
        r'(월요일|화요일|수요일|목요일|금요일|토요일|일요일)',  # 요일
    ]

    found_dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, content)
        found_dates.extend(matches)

    return found_dates

def validate_date_consistency(mcp_data: str, notion_content: str, expected_date: str = None) -> Dict:
    """MCP 데이터와 Notion 내용의 날짜 일치성 검증"""

    mcp_dates = extract_date_from_content(mcp_data)
    notion_dates = extract_date_from_content(notion_content)

    # 어제 날짜 계산
    yesterday = date.today().strftime('%Y-%m-%d')
    if expected_date:
        yesterday = expected_date

    # 날짜 일치성 확인
    mcp_has_expected = any(yesterday in str(mcp_dates) for d in mcp_dates)
    notion_has_expected = any(yesterday in str(notion_dates) for d in notion_dates)

    return {
        "date_consistent": mcp_has_expected and notion_has_expected,
        "expected_date": yesterday,
        "mcp_dates": mcp_dates,
        "notion_dates": notion_dates,
        "mcp_has_expected": mcp_has_expected,
        "notion_has_expected": notion_has_expected
    }

def validate_top10_products(mcp_data: str, notion_content: str) -> Dict:
    """Top 10 상품 리스트 완전성 검증"""

    # MCP에서 Top 10 상품 수 확인
    mcp_top10_pattern = r'(\d+)\.\s*\*\*\[.*?\].*?\*\*.*?GMV.*?(\d+,\d+|\d+).*?원'
    mcp_products = re.findall(mcp_top10_pattern, mcp_data)

    # Notion에서 Top 10 상품 수 확인
    notion_top10_pattern = r'(\d+)\.\s*\*\*\[.*?\].*?\*\*.*?GMV.*?(\d+,\d+|\d+).*?원'
    notion_products = re.findall(notion_top10_pattern, notion_content)

    return {
        "top10_complete": len(mcp_products) == len(notion_products) and len(mcp_products) >= 8,
        "mcp_product_count": len(mcp_products),
        "notion_product_count": len(notion_products),
        "minimum_threshold_met": len(notion_products) >= 8
    }

def validate_brand_completeness(mcp_data: str, notion_content: str) -> Dict:
    """브랜드 데이터 완전성 강화 검증"""

    # 필수 브랜드 목록
    required_brands = ['노어', '다나앤페타', '마치마라', '브에트와', '아르앙', '지재', '희애']
    optional_brands = ['퀸즈셀렉션', '베르다']

    mcp_brands_found = []
    notion_brands_found = []

    for brand in required_brands + optional_brands:
        # MCP에서 브랜드 데이터 확인 (GMV 포함)
        mcp_pattern = rf'{brand}.*?GMV.*?(\d+,\d+|\d+).*?원'
        if re.search(mcp_pattern, mcp_data):
            mcp_brands_found.append(brand)

        # Notion에서 브랜드 데이터 확인
        notion_pattern = rf'\*\*{brand}\*\*.*?GMV.*?(\d+,\d+|\d+).*?원'
        if re.search(notion_pattern, notion_content):
            notion_brands_found.append(brand)

    # 필수 브랜드 누락 확인
    missing_required = [b for b in required_brands if b not in notion_brands_found]

    return {
        "brands_complete": len(missing_required) == 0,
        "mcp_brands_count": len(mcp_brands_found),
        "notion_brands_count": len(notion_brands_found),
        "required_brands_found": [b for b in required_brands if b in notion_brands_found],
        "missing_required_brands": missing_required,
        "optional_brands_found": [b for b in optional_brands if b in notion_brands_found]
    }

def validate_completeness(mcp_sections: Set[str], notion_sections: Set[str]) -> Dict:
    """완전성 검증 및 결과 반환"""
    missing_sections = mcp_sections - notion_sections
    extra_sections = notion_sections - mcp_sections

    # 필수 섹션 정의 (MCP에 있으면 Notion에도 반드시 있어야 함)
    critical_sections = {
        "brand_snapshots", "top_performers", "urgent_priorities",
        "action_items", "sufficient_brands"
    }

    missing_critical = missing_sections & critical_sections

    is_complete = len(missing_critical) == 0
    completeness_score = (len(notion_sections) / max(len(mcp_sections), 1)) * 100

    return {
        "is_complete": is_complete,
        "completeness_score": round(completeness_score, 1),
        "missing_sections": list(missing_sections),
        "missing_critical": list(missing_critical),
        "mcp_section_count": len(mcp_sections),
        "notion_section_count": len(notion_sections)
    }

def main():
    """메인 실행 함수"""
    if len(sys.argv) < 3:
        print("Usage: python3 notion_content_validator.py <mcp_data_file> <notion_content_file> [expected_date]")
        sys.exit(1)

    mcp_file, notion_file = sys.argv[1], sys.argv[2]
    expected_date = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        # MCP 데이터 읽기
        with open(mcp_file, 'r', encoding='utf-8') as f:
            mcp_data = f.read()

        # Notion 내용 읽기
        with open(notion_file, 'r', encoding='utf-8') as f:
            notion_content = f.read()

    except FileNotFoundError as e:
        print(f"ERROR: 파일을 찾을 수 없습니다 - {e}")
        sys.exit(11)
    except Exception as e:
        print(f"ERROR: 파일 읽기 실패 - {e}")
        sys.exit(12)

    # 섹션 추출
    mcp_sections = extract_mcp_sections(mcp_data)
    notion_sections = extract_notion_sections(notion_content)

    # 기본 완전성 검증
    result = validate_completeness(mcp_sections, notion_sections)

    # 강화된 검증 실행
    validation_results = {
        "basic_completeness": result
    }

    # 날짜 일치성 검증
    date_validation = validate_date_consistency(mcp_data, notion_content, expected_date)
    validation_results["date_consistency"] = date_validation

    # Top 10 상품 완전성 검증
    top10_validation = validate_top10_products(mcp_data, notion_content)
    validation_results["top10_products"] = top10_validation

    # 브랜드 데이터 완전성 검증
    brand_validation = validate_brand_completeness(mcp_data, notion_content)
    validation_results["brand_completeness"] = brand_validation

    # 전체 검증 결과 계산
    all_validations_passed = (
        result["is_complete"] and
        date_validation["date_consistent"] and
        top10_validation["top10_complete"] and
        brand_validation["brands_complete"]
    )

    # 결과 출력
    print(f"📊 Notion 보고서 검증 결과")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if all_validations_passed:
        print("✅ PASS: 모든 검증을 통과했습니다")
        print(f"• 기본 완전성: {result['completeness_score']}%")
        print(f"• 날짜 일치성: ✅ 통과")
        print(f"• Top 10 상품: {top10_validation['notion_product_count']}개")
        print(f"• 브랜드 데이터: {brand_validation['notion_brands_count']}개 브랜드")
        sys.exit(0)
    else:
        print("❌ FAIL: 일부 검증에 실패했습니다")

        # 기본 완전성
        print(f"• 기본 완전성: {result['completeness_score']}% ({'✅' if result['is_complete'] else '❌'})")
        if not result["is_complete"]:
            print(f"  - 누락된 핵심 섹션: {result['missing_critical']}")

        # 날짜 일치성
        print(f"• 날짜 일치성: {'✅' if date_validation['date_consistent'] else '❌'}")
        if not date_validation["date_consistent"]:
            print(f"  - 예상 날짜: {date_validation['expected_date']}")
            print(f"  - MCP 날짜: {date_validation['mcp_dates']}")
            print(f"  - Notion 날짜: {date_validation['notion_dates']}")

        # Top 10 상품
        print(f"• Top 10 상품: {'✅' if top10_validation['top10_complete'] else '❌'}")
        print(f"  - MCP: {top10_validation['mcp_product_count']}개")
        print(f"  - Notion: {top10_validation['notion_product_count']}개")

        # 브랜드 완전성
        print(f"• 브랜드 완전성: {'✅' if brand_validation['brands_complete'] else '❌'}")
        print(f"  - 필수 브랜드: {len(brand_validation['required_brands_found'])}/7개")
        if brand_validation['missing_required_brands']:
            print(f"  - 누락된 브랜드: {brand_validation['missing_required_brands']}")

        sys.exit(13)

if __name__ == "__main__":
    main()