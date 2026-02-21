#!/usr/bin/env python3
"""
Slack 메시지 6단어 이하 규칙 + 필수 요소 검증 스크립트
2025-09-09 업데이트: 6단어 이하 규칙 강제 검증 추가
"""

import re
import sys
import json

def validate_6_word_rule(message_text):
    """6단어 이하 규칙 검증 (설명문만, 고유명사/데이터라벨 제외)"""
    
    # 문장 분리 (줄바꿈과 마침표 기준)
    sentences = re.split(r'\n|\.', message_text)
    violations = []
    
    # 보존 대상 패턴 (6단어 규칙 적용하지 않음)
    preserve_patterns = [
        r'\[.*\]',                              # [브랜드명], [상품명] 등 대괄호
        r'비중:.*\|.*',                         # 비중: GMV x% | 노출 x%
        r'점유율:.*\|.*\|.*',                   # 점유율: 기획전 x% | MD x% | 개인화 x%
        r'GMV.*억.*만원',                       # GMV 절대값 (x억x만원)
        r'SPV.*\(',                             # SPV 수치 (괄호 포함)
        r'https?://',                           # URL 링크
        r'<!subteam',                           # Slack 그룹 알림
        r'^\s*[-\d]+\.',                        # 번호가 매겨진 리스트
        r'^\s*[•\-\*]',                         # 불릿 포인트
        r'📋.*상세.*분석',                      # 상세분석 링크 라인
    ]
    
    for sentence in sentences:
        # 불필요한 공백 제거 및 빈 문장 제외
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # 보존 대상 패턴 체크
        should_preserve = False
        for pattern in preserve_patterns:
            if re.search(pattern, sentence):
                should_preserve = True
                break
        
        if should_preserve:
            continue
            
        # 마크다운 문법, 이모지, URL 등 제외하고 실제 단어만 추출
        clean_sentence = re.sub(r'[*#\-\[\](){}]', '', sentence)  # 마크다운 제거
        clean_sentence = re.sub(r'http[s]?://\S+', '', clean_sentence)  # URL 제거
        clean_sentence = re.sub(r'<[^>]+>', '', clean_sentence)  # HTML 태그 제거
        clean_sentence = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF🔥🧊🔼🔽↔️🚀]', '', clean_sentence)  # 이모지 제거
        
        # 공백 기준 단어 개수 계산
        words = [word for word in clean_sentence.split() if word.strip()]
        
        if len(words) > 6:
            violations.append(f"'{sentence.strip()}' ({len(words)}단어)")
    
    return violations

def validate_slack_message(message_text):
    """Slack 메시지 필수 요소 검증 (6단어 규칙 적용)"""
    
    # 6단어 이하 규칙 검증
    word_violations = validate_6_word_rule(message_text)
    if word_violations:
        print(f"🚨 6단어 이하 규칙 위반:")
        for violation in word_violations:
            print(f"  - {violation}")
        return False
    
    # 필수 패턴 검증 (6단어 템플릿 + 3채널 점유율)
    required_patterns = [
        r"비중:.*GMV.*\|.*노출",                              # 어제 비중 정보
        r"점유율:.*기획전.*\|.*MD.*\|.*개인화",                # 노출 점유율 (3채널 모두)
        r"🔥 Top 급성장",                                    # 급성장 상품 섹션
        r"Looker Studio.*lookerstudio\.google\.com",          # Looker Studio 링크
        r"<!subteam\^<YOUR_SLACK_SUBTEAM_ID>>"                           # 그룹 알림
    ]
    
    missing_elements = []
    element_names = ["비중 정보", "3채널 점유율", "급성장 상품", "Looker Studio 링크", "그룹 알림"]
    
    for i, pattern in enumerate(required_patterns):
        if not re.search(pattern, message_text):
            missing_elements.append(element_names[i])
    
    if missing_elements:
        print(f"🚨 필수 요소 누락: {', '.join(missing_elements)}")
        return False
    
    print("✅ 6단어 규칙 + 필수 요소 검증 통과")
    return True

def generate_efficiency_lines_6word(mcp_data):
    """6단어 이하 비중 라인 자동 생성"""
    
    try:
        # 어제 비중 (6단어 이하)
        yesterday_ratio = mcp_data["overall_pb_summary"]["yesterday_performance"]["ratio_efficiency"]
        yesterday_line = f"  비중: GMV {yesterday_ratio['gmv_share']}% | 노출 {yesterday_ratio['vcnt_share']}%"
        
        # 점유율 (6단어 이하)  
        yesterday_exposure = mcp_data["overall_pb_summary"]["yesterday_performance"]["exposure_share"]
        exposure_line = f"  점유율: 기획전 {yesterday_exposure['exhibition']}% | MD {yesterday_exposure['md_boost']}%"
        
        return yesterday_line, exposure_line
        
    except KeyError as e:
        print(f"❌ MCP 데이터에서 비중 정보 누락: {e}")
        return None, None

def test_6word_sample():
    """6단어 이하 템플릿 샘플 테스트 (선택적 적용)"""
    
    sample_message = """📰 **PB 데일리 인텔리전스 브리핑 (2025-09-09 (월요일))**

> 📌 PB GMV -14% 🧊  
> MVP: **[지재] [BEST/77까지] 인밴딩 H라인 스판 데님 스커트 +43% 🚀**

---

**📊 전체 PB 성과**
- **어제**: GMV 2,520만원 (-14% 🧊), SPV 13.05 (+1% 🔼)
  비중: GMV 2.34% | 노출 3.29%  
  점유율: 기획전 2.72% | MD 9.46% | 개인화 3.07%
- **주간**: GMV 2억3,693만원 (+18% 🔼), SPV 13.09

---

**🔥 Top 급성장 (5개)**  
1. [지재] [BEST/77까지] 인밴딩 H라인 스판 데님 스커트 +45% 🔥
2. [지재] 와이드핏 랩 슬랙스 프리미엄 코튼 블렌드 +186% 🔥  

---

📋 **상세분석**: [Notion](notion_url) | [Looker Studio](https://lookerstudio.google.com/u/1/reporting/<YOUR_LOOKER_REPORT_ID>/page/p_68mmtt2ovd)

<!subteam^<YOUR_SLACK_SUBTEAM_ID>>"""

    return validate_slack_message(sample_message)

def main():
    """메인 실행 함수"""
    
    # 테스트 모드 확인
    if len(sys.argv) == 2 and sys.argv[1] == "--test":
        print("🧪 6단어 이하 템플릿 샘플 테스트 실행...")
        is_valid = test_6word_sample()
        sys.exit(0 if is_valid else 1)
        
    if len(sys.argv) < 2:
        print("Usage: python3 slack_message_validator.py 'slack_message_text'")
        print("       python3 slack_message_validator.py --test")
        sys.exit(1)
    
    message_text = sys.argv[1]
    
    # Slack 메시지 6단어 규칙 + 필수 요소 검증
    is_valid = validate_slack_message(message_text)
    
    if is_valid:
        print("🎉 6단어 이하 슬랙 메시지 검증 통과!")
        sys.exit(0)
    else:
        print("💥 6단어 이하 슬랙 메시지 검증 실패!")
        sys.exit(1)

if __name__ == "__main__":
    main()