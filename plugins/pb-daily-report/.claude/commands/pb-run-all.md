---
allowed-tools: Bash, mcp__plugin_Notion_notion__notion-create-pages, mcp__slack__conversations_add_message, Write, Read
description: Execute complete PB daily report workflow (All 3 steps) - v7.2
argument-hint: [execution_date YYYY-MM-DD]
---

# PB Daily Report - Complete Workflow v7.2

Execute all steps: BigQuery + Gemini → Notion → Slack

**New in v7.2**:
- 날짜 처리 규칙 명확화: `analysis_date = execution_date - 1`
- Gemini raw markdown 응답 형식 지원
- 타임아웃 10분으로 연장

**References**: See `_references/` for details:
- `config.md` - IDs, URLs, brands, units
- `templates.md` - Slack/Notion 형식 + JSON→Markdown 변환
- `validation.md` - All validation scripts
- `data-flow.md` - Step-by-step data flow

---

## ⚠️ Critical Rules (v7.0)

| Step | CRITICAL Rule |
|------|---------------|
| Step 1 | **report_generator.py 실행** (BigQuery + Gemini) |
| Step 1 | **⚠️ fix_day_of_week.py 실행 필수** |
| Step 2 | **⚠️ convert_mcp_to_notion.py 스크립트 실행 필수** (수동 변환 금지) |
| Step 2 | **요일 계산은 반드시 Python datetime 사용** (Claude 추론 금지) |
| Step 2 | validation 파일에 fix_day_of_week.py 실행 필수 |
| Step 3 | **`_references/templates.md` 먼저 Read 필수** |
| Step 3 | `content_type: text/plain` 필수 |
| Step 3 | 9개 브랜드 스레드 모두 발송 필수 |

---

## Quick Checklist

- [ ] **report_generator.py 실행** (Step 1 - 새로운 방식)
- [ ] fix_day_of_week.py 실행 (MCP 파일)
- [ ] validate_mcp_raw.py after Step 1
- [ ] **⚠️ convert_mcp_to_notion.py 실행** (Step 2 - 수동 변환 금지!)
- [ ] **변환 검증 리포트 확인** (9 섹션, 8 채널, 9 브랜드, 10 상품)
- [ ] **⚠️ 요일은 Python datetime으로 계산** (Claude 추론 금지)
- [ ] Notion ancestor-path verified
- [ ] validation-YYYY-MM-DD.json saved
- [ ] **⚠️ fix_day_of_week.py validation 파일에 실행**
- [ ] **⚠️ Read `_references/templates.md` BEFORE Step 3**
- [ ] **content_type: text/plain** (Step 3)
- [ ] **Template compliance verified** (Step 3)
- [ ] **9 brand threads sent** (Step 3)

---

## Step 1: Data Generation (v7.2)

### ⚠️ 날짜 규칙 (CRITICAL)

| 용어 | 설명 | 예시 (1월 27일 실행) |
|------|------|---------------------|
| `execution_date` | 실행일 (인자로 전달) | 2026-01-27 |
| `analysis_date` | 분석 대상일 = 실행일 - 1 | 2026-01-26 (월요일) |

**Notion/Slack에는 `analysis_date`로 표시!**

### 1.1 Run Python Report Generator (⚠️ 타임아웃 10분)

```bash
# 인자 없이 실행 → 어제(analysis_date) 자동 계산
python3 ~/.pb-reports/scripts/report_generator.py
```

**Output**: `~/.pb-reports/mcp-raw-{analysis_date}.json`

**타임아웃**: 10분 (600000ms) - BigQuery + Gemini 응답 대기

### 1.2 Fix Day of Week (⚠️ MANDATORY)

```bash
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/mcp-raw-{analysis_date}.json
```

### 1.3 Validate

```bash
python3 ~/.pb-reports/validate_mcp_raw.py ~/.pb-reports/mcp-raw-{analysis_date}.json
```

---

## Step 2: Notion Page Creation

### 2.1 Run Conversion Script (⚠️ MANDATORY)

```bash
python3 ~/.pb-reports/convert_mcp_to_notion.py ~/.pb-reports/mcp-raw-{analysis_date}.json
```

**출력 파일**: `~/.pb-reports/notion-content-{analysis_date}.md`

**검증 리포트 확인**:
- 모든 9개 섹션이 `✓`로 표시되어야 함
- `channel_exposure_yesterday`: 8 채널
- `brand_snapshot`: 9 브랜드
- `top_10_products`: 10 상품
- `portfolio_stage_briefing`: ✓ 추가됨

**Gemini raw markdown 형식 (v7.2)**:
- Gemini가 `daily_intelligence_briefing`을 전체 마크다운 문자열로 반환할 수 있음
- 변환 스크립트가 자동으로 처리: `pb_intel_report: ✓ (raw markdown 형식)`

**⚠️ 스크립트 실행 없이 수동 변환 금지!**

### 2.2 Notion 페이지 생성

1. **Load** 변환된 콘텐츠 파일 (`notion-content-{analysis_date}.md`)
2. **⚠️ 요일 계산 (Python 필수)** - analysis_date 기준:
   ```bash
   python3 -c "from datetime import datetime; d=datetime(YYYY,MM,DD); days=['월요일','화요일','수요일','목요일','금요일','토요일','일요일']; print(f'{d:%Y-%m-%d} ({days[d.weekday()]})')"
   ```
   **❌ NEVER**: Claude가 직접 요일 추론 (하루 밀림 버그 있음)
3. **Title**: `PB Daily Report - {analysis_date} (Python으로 계산된 요일)`
4. **Create** with `data_source_id: <YOUR_NOTION_DATASOURCE_ID>`
5. **Verify**: ancestor-path NOT empty
6. **Save**: `validation-{analysis_date}.json` with 9 brands, 10 products
   - **⚠️ summary에 반드시 포함**: `gmv_share` (mcp-raw → `summary.share.GMV`), `spv_vs_md2` (mcp-raw → `summary.share.SPV_vs_MD2`)
7. **⚠️ Fix validation 요일**: `python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/validation-{analysis_date}.json`

**❌ NEVER**: 수동으로 JSON → Markdown 변환 (스크립트 사용 필수)
**❌ NEVER**: Save raw JSON to Notion (unreadable)
**❌ NEVER**: Claude가 직접 요일 추론 (반드시 Python datetime 사용)
**❌ NEVER**: 실행일(execution_date)을 분석 대상일로 사용

---

## Step 3: Slack Distribution

**Pre-flight**: JSON file MUST exist at `~/.pb-reports/validation-YYYY-MM-DD.json`

### ⚠️ MANDATORY: Read Template First
```
Read(_references/templates.md) ← 반드시 먼저 읽기!
```
**템플릿 파일을 읽지 않으면 Step 3 진행 금지**

### Execution Order
1. **READ TEMPLATE**: `_references/templates.md` 파일을 Read tool로 먼저 읽기
2. **Load** from validation JSON
3. **Build** main message using exact template format
4. **Send** main briefing with **`content_type: text/plain`**
5. **Get** thread_ts from response
6. **Build** 9 brand threads using exact template format
7. **Send** 9 brand threads (ALL required) as replies

### Template Compliance Checklist (발송 전 확인)
- [ ] `:newspaper:` 헤더로 시작
- [ ] `━━━━` 구분선 2개
- [ ] MVP 라인: `*PB GMV {±%}%* | *MVP: {브랜드} {±%}%*`
- [ ] `:bar_chart:`, `:rocket:`, `:rotating_light:`, `:clipboard:` 섹션
- [ ] `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` 그룹 태그 (NOT `subteam<YOUR_SLACK_SUBTEAM_ID>`)
- [ ] 브랜드 스레드 3줄: `• 어제:`, `• 주간:`, `• 노출:`

**❌ NEVER**: Use `content_type: text/markdown`
**❌ NEVER**: Skip reading templates.md

---

## Error Handling

| Step | Error | Action |
|------|-------|--------|
| 1 | BigQuery auth fail | `gcloud auth application-default login` |
| 1 | Gemini fail | Check `GEMINI_API_KEY` env |
| 1 | 타임아웃 | 타임아웃 10분으로 연장 (600000ms) |
| 1.3 | Validation fail | Re-check BigQuery data |
| 2.1 | Conversion script fail | Check MCP raw JSON structure |
| 2.1 | `'str' object has no attribute 'items'` | Gemini raw markdown 형식 - converters 업데이트 필요 |
| 2.1 | 섹션 누락 | Re-run conversion, check validation report |
| 2 | 수동 변환 시도 | Stop, run conversion script instead |
| 2 | 날짜가 하루 밀림 | analysis_date = execution_date - 1 확인 |
| 2.5 | Personal page | Stop, re-create with data_source_id |
| 3 | JSON missing | Go back to Step 2.6 |
| 3 | 링크/멘션 깨짐 | content_type 확인, text/plain 사용 |

---

## Data Source Rules (v7.2)

| Step | ONLY Source | NEVER Use |
|------|-------------|-----------|
| 1 | BigQuery + Gemini (Python script) | MCP directly |
| 2.1 | mcp-raw-*.json | Memory |
| 2.2 | notion-content-*.md (스크립트 출력) | 수동 변환, raw JSON |
| 3 | validation-*.json | Notion fetch, MCP |

**Lineage**: BigQuery → Gemini → mcp-raw.json → **convert_mcp_to_notion.py** → notion-content.md → Notion → validation.json → Slack

---

## Changelog (v7.2)

| 날짜 | 변경 사항 |
|------|-----------|
| 2026-01-27 | **v7.2**: 날짜 규칙 명확화 (analysis_date = execution_date - 1) |
| 2026-01-27 | converters/base.py: Gemini raw markdown 형식 지원 추가 |
| 2026-01-27 | converters/sections.py: `_raw_markdown` 케이스 처리 추가 |
| 2026-01-27 | convert_mcp_to_notion.py: validation report 업데이트 |
| 2026-01-27 | 타임아웃 5분 → 10분 권장 |

---

*Last updated: 2026-01-27 | v7.2 | 날짜 규칙 명확화, Gemini raw markdown 지원*
