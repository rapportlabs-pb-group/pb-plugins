---
paths:
  - .claude/commands/**
  - CLAUDE.md
  - scripts/**
  - "~/.pb-reports/**"
---

# PB Workflow Rules

PB Daily Report 워크플로우에서 반드시 지켜야 할 규칙입니다.

## ⚠️ MCP 사용 금지 (v7.1)

`mcp__Pb_daily_report_mcp__daily_report_maker` 및 `daily_report_maker_2` MCP 도구 **사용 금지**.
반드시 Python 스크립트(`report_generator.py`)만 사용.

## 필수 스크립트 사용

| 단계 | 스크립트 | 목적 |
|------|----------|------|
| Step 1 | `report_generator.py` | BigQuery + Gemini 리포트 생성 |
| Step 1 | `fix_day_of_week.py` | 요일 버그 수정 |
| Step 1 | `validate_mcp_raw.py` | 데이터 검증 |
| Step 2 | `convert_mcp_to_notion.py` | JSON→Markdown 변환 |

## 금지 사항

- **MCP 도구 사용** (daily_report_maker 등)
- 수동 JSON→Markdown 변환
- Claude 추론으로 요일 계산
- 템플릿 형식 임의 변경
- 9개 미만 브랜드 스레드 전송

## 브랜드 목록

**허용**: 노어, 다나앤페타, 마치마라, 베르다, 브에트와, 아르앙, 지재, 퀸즈셀렉션, 희애

**금지**: 오드리나, 더블유온, 에일린, 헨리, 오르시, 로이드

## Slack 형식

- `content_type: text/plain` 필수
- 그룹 태그: `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>`
