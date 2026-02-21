#!/usr/bin/env python3
"""
Duplicate Checker - PB Daily Report 중복 생성 방지

Notion에서 해당 날짜의 PB Daily Report가 이미 존재하는지
확인하여 중복 생성을 방지합니다.
"""

import json
import sys
import subprocess
import time

def search_existing_pages(date_str, title=None, claude_path="claude"):
    """Notion에서 해당 날짜의 페이지가 이미 존재하는지 확인"""

    search_queries = [
        f"PB Daily Report {date_str}",
        f"PB Daily Report - {date_str}",
        date_str
    ]

    if title:
        search_queries.insert(0, title)

    found_pages = []

    for query in search_queries:
        try:
            # Notion 검색 실행
            cmd = [
                claude_path,
                "-p", f'mcp__notionMCP__notion-search로 "{query}" 검색하여 결과를 JSON으로 반환하세요. query_type은 internal로 설정하세요.',
                "--output-format", "json",
                "--max-turns", "3",
                "--permission-mode", "bypassPermissions",
                "--allowedTools", "mcp__notionMCP"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                continue

            # 결과 파싱
            try:
                output = json.loads(result.stdout)
                result_str = output.get("result", "")

                # result가 JSON 문자열인 경우 다시 파싱
                if isinstance(result_str, str) and result_str.strip().startswith('{'):
                    search_results = json.loads(result_str)
                elif isinstance(result_str, dict):
                    search_results = result_str
                else:
                    continue

                # 검색 결과 분석
                if "results" in search_results:
                    for item in search_results["results"]:
                        page_title = item.get("title", "")
                        page_id = item.get("id", "")
                        page_url = item.get("url", "")

                        # 날짜가 정확히 일치하는지 확인
                        if date_str in page_title and "PB Daily Report" in page_title:
                            found_pages.append({
                                "id": page_id,
                                "title": page_title,
                                "url": page_url,
                                "timestamp": item.get("timestamp"),
                                "search_query": query
                            })

            except json.JSONDecodeError:
                continue

        except subprocess.TimeoutExpired:
            print(f"WARNING: 검색 타임아웃 - query: {query}")
            continue
        except Exception as e:
            print(f"WARNING: 검색 실패 - query: {query}, error: {e}")
            continue

        # 검색 간 잠시 대기
        time.sleep(1)

    # 중복 제거 (같은 ID인 경우)
    unique_pages = {}
    for page in found_pages:
        page_id = page["id"]
        if page_id not in unique_pages:
            unique_pages[page_id] = page

    return list(unique_pages.values())

def check_duplicate_by_date(date_str, title=None):
    """날짜 기반으로 중복 페이지 확인"""

    print(f"🔍 중복 페이지 검색 중... (날짜: {date_str})")

    try:
        existing_pages = search_existing_pages(date_str, title)

        if not existing_pages:
            return {
                "has_duplicate": False,
                "message": f"✅ 중복 없음: {date_str} 날짜의 PB Daily Report가 없습니다.",
                "date": date_str,
                "search_count": 0
            }

        # 가장 최근 페이지 선택
        latest_page = max(existing_pages, key=lambda x: x.get("timestamp", ""))

        return {
            "has_duplicate": True,
            "message": f"⚠️ 중복 발견: {date_str} 날짜의 PB Daily Report가 이미 존재합니다.",
            "date": date_str,
            "search_count": len(existing_pages),
            "existing_pages": existing_pages,
            "latest_page": latest_page,
            "recommendation": "기존 페이지 업데이트 또는 실행 건너뛰기"
        }

    except Exception as e:
        return {
            "has_duplicate": False,
            "error": True,
            "message": f"❌ 중복 검사 실패: {str(e)}",
            "date": date_str,
            "recommendation": "안전을 위해 실행 진행"
        }

def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("Usage: python3 duplicate_checker.py <date> [title]")
        print("Example: python3 duplicate_checker.py 2025-09-22 'PB Daily Report - 2025-09-22 (월요일)'")
        sys.exit(1)

    date_str = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None

    # 날짜 형식 검증
    try:
        from datetime import datetime
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print(f"❌ ERROR: 잘못된 날짜 형식: {date_str} (YYYY-MM-DD 형식 필요)")
        sys.exit(2)

    # 중복 검사 실행
    result = check_duplicate_by_date(date_str, title)

    # 결과 출력
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 종료 코드 설정
    if result.get("has_duplicate", False):
        # 중복 발견 시 종료 코드 20
        sys.exit(20)
    elif result.get("error", False):
        # 에러 발생 시 종료 코드 21
        sys.exit(21)
    else:
        # 중복 없음 - 정상 진행
        sys.exit(0)

if __name__ == "__main__":
    main()