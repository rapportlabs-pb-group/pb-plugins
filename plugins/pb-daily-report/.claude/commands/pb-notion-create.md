---
allowed-tools: mcp__plugin_Notion_notion__notion-create-pages, Read, Bash
description: Create Notion page with report content (Step 2) - v6.5
argument-hint: [date YYYY-MM-DD]
---

# PB Daily Report - Step 2: Notion Page Creation v6.5

**References**:
- `_references/config.md` - Database ID, data source ID
- `_references/templates.md` - JSON → Markdown 변환 예시
- `_references/validation.md` - Verification rules

---

## Critical Requirements

### Parent Specification (MANDATORY)
```json
{"parent": {"data_source_id": "<YOUR_NOTION_DATASOURCE_ID>"}}
```
Without this: Page becomes personal page, not in database.

### Data Source
```bash
MCP_FILE=~/.pb-reports/mcp-raw-YYYY-MM-DD.json
```
**MUST load from file, NOT memory.**

---

## Execution Steps

### 1. Run Conversion Script (⚠️ MANDATORY - v6.5)

```bash
python3 ~/.pb-reports/convert_mcp_to_notion.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
```

**출력 파일**: `~/.pb-reports/notion-content-YYYY-MM-DD.md`

**검증 리포트 확인**:
- 모든 9개 섹션이 `✓`로 표시되어야 함
- `channel_exposure_yesterday`: 8 채널
- `brand_snapshot`: 9 브랜드
- `top_10_products`: 10 상품
- `portfolio_stage_briefing`: ✓ 추가됨

**⚠️ 스크립트 실행 없이 수동 변환 금지!**

### 2. Load Converted Content

```bash
CONTENT_FILE=~/.pb-reports/notion-content-YYYY-MM-DD.md
```

Read tool로 변환된 콘텐츠 파일을 로드합니다.

### 3. Generate Title (⚠️ Python datetime 필수!)

**❌ NEVER**: Claude가 직접 요일 추론 (하루 밀림 버그 있음)
**✅ ALWAYS**: Python datetime으로 계산

```bash
# 반드시 이 명령어로 요일 확인 후 제목 생성!
python3 -c "from datetime import datetime; d=datetime(YYYY,MM,DD); days=['월요일','화요일','수요일','목요일','금요일','토요일','일요일']; print(f'PB Daily Report - {d:%Y-%m-%d} ({days[d.weekday()]})')"
```

예시:
```bash
python3 -c "from datetime import datetime; d=datetime(2026,1,11); days=['월요일','화요일','수요일','목요일','금요일','토요일','일요일']; print(f'PB Daily Report - {d:%Y-%m-%d} ({days[d.weekday()]})')"
# Output: PB Daily Report - 2026-01-11 (일요일)
```

### 4. Create Page
```json
{
  "parent": {"data_source_id": "<YOUR_NOTION_DATASOURCE_ID>"},
  "pages": [{
    "properties": {"이름": "PB Daily Report - YYYY-MM-DD (요일)"},
    "content": "[notion-content-YYYY-MM-DD.md 파일 내용]"
  }]
}
```

### 5. Verify
- `ancestor-path` NOT empty
- `properties` contains `이름`

### 6. Save Validation JSON

```bash
~/.pb-reports/validation-YYYY-MM-DD.json
```

### 7. Fix Validation Day of Week (⚠️ MANDATORY)

```bash
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/validation-YYYY-MM-DD.json
```

---

## ❌ FORBIDDEN

| DO NOT | REASON |
|--------|--------|
| 수동으로 JSON → Markdown 변환 | 필드 누락 위험, 스크립트 사용 필수 |
| pb_intel_report JSON 그대로 저장 | JSON은 사람이 읽을 수 없음 |
| 메모리에서 데이터 사용 | 파일 기반 SSOT 위반 |

---

## Failure Actions

| Issue | Action |
|-------|--------|
| MCP file missing | Run Step 1 first |
| Conversion script fails | Check MCP raw JSON structure |
| Content missing sections | Re-run conversion script, check report |
| Personal page created | Delete, re-create with data_source_id |

---

*Last updated: 2026-01-14 | v6.5 | Python script for deterministic conversion*
