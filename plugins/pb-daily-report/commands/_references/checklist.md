# Execution Checklist

워크플로우 실행 시 확인해야 할 체크리스트입니다.

## Step 1: MCP 데이터 생성

- [ ] Write tool로 MCP 저장
- [ ] **fix_day_of_week.py 실행** (MCP 버그 수정)
- [ ] validate_mcp_raw.py 실행

## Step 2: Notion 페이지 생성

- [ ] **convert_mcp_to_notion.py 실행** (수동 변환 금지!)
- [ ] **변환 검증 리포트 확인** (9 섹션, 8 채널, 9 브랜드, 10 상품)
- [ ] **요일은 Python datetime으로 계산** (Claude 추론 금지!)
- [ ] Notion ancestor-path 확인
- [ ] **validation 파일에 fix_day_of_week.py 실행**

## Step 3: Slack 발송

- [ ] **`_references/templates.md` Read 필수**
- [ ] **content_type: text/plain**
- [ ] **템플릿 형식 정확히 준수** (구분선, 불릿, 볼드, 링크 형식)
- [ ] **9개 브랜드 스레드 전송 (4줄 구조: 어제/주간/노출/코호트)**
- [ ] **주간 데이터에 `weekly_brand_data` metadata 사용**
- [ ] **코호트 데이터에 `season_cohort_data` metadata 사용**

## Slack 템플릿 필수 요소

| 요소 | 올바른 형식 | 잘못된 형식 |
|------|-------------|-------------|
| 구분선 | `━━━━━━━━━━━━━━━━━━━━` | (없음) |
| 불릿 | `• 어제:` | ` 어제:` |
| 볼드 | `*PB GMV*` | `PB GMV` |
| 링크 | `<URL\|Text>` | `URL - Text` |
| 그룹태그 | `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` | `subteam<YOUR_SLACK_SUBTEAM_ID>` |

---
*Extracted from CLAUDE.md v7.3*
