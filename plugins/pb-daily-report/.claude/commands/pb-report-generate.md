---
allowed-tools: Bash, Write
description: Generate PB daily report content (Step 1) - v7.0
argument-hint: [optional date YYYY-MM-DD]
---

# PB Daily Report - Step 1: Content Generation v7.0

**New in v7.0**: n8n 워크플로우를 Python 스크립트로 마이그레이션
- BigQuery 쿼리 2개 (v7.7 + v2.0) → Gemini CLI → MCP-compatible JSON
- MCP 대신 로컬 Python 실행 (안정성 향상)

**References**:
- `_references/config.md` - File paths, units
- `_references/data-flow.md` - MCP data structure
- `_references/validation.md` - Integrity checks

---

## Execution Steps

### 1. Run Python Report Generator

```bash
python3 ~/.pb-reports/scripts/report_generator.py [YYYY-MM-DD]
```

**No date argument**: Yesterday's report is generated.

Example:
```bash
# Generate for yesterday
python3 ~/.pb-reports/scripts/report_generator.py

# Generate for specific date
python3 ~/.pb-reports/scripts/report_generator.py 2026-01-25
```

**Output**: `~/.pb-reports/mcp-raw-YYYY-MM-DD.json`

### 2. Fix Day of Week (⚠️ MANDATORY)

**⚠️ 필수**: Gemini 모델이 요일을 직접 추론하면 오류가 발생할 수 있습니다.

```bash
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
```

### 3. Validate

```bash
python3 ~/.pb-reports/validate_mcp_raw.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
```

Checks:
- JSON valid
- Required keys present (`pb_intel_report`, `portfolio_stage_briefing`, `metadata`)
- No placeholders
- Minimum length (pb > 500 chars, portfolio > 1000 chars)

---

## Architecture (v7.0)

```
BigQuery (pb_portfolio_v7.7.sql) ─┬─→ Gemini CLI → pb_intel_report
     (병렬 실행)                  │
BigQuery (pb_dashboard_v2.0.sql) ─┴─→ Gemini CLI → portfolio_stage_briefing
                                            ↓
                                  mcp-raw-YYYY-MM-DD.json
                                            ↓
                                  기존 워크플로우 유지
                           (fix_day_of_week → convert_mcp_to_notion → Notion → Slack)
```

---

## Output Structure (MCP-compatible)

```json
{
  "generated_at": "2026-01-26T00:00:00.000Z",
  "pb_intel_report": {
    "parts": [{"text": "```json\n{...}\n```"}],
    "role": "model"
  },
  "portfolio_stage_briefing": {
    "parts": [{"text": "**Markdown content...**"}],
    "role": "model"
  },
  "metadata": {
    "analysis_date": "YYYY-MM-DD",
    "execution_date": "YYYY-MM-DD"
  }
}
```

---

## Date Rule

```
analysis_date = execution_date - 1 day
```

---

## Dependencies

- **Python 3.9+**
- **google-cloud-bigquery**: `pip install google-cloud-bigquery`
- **Gemini CLI**: `npm install -g @anthropic-ai/gemini`
- **GCP Auth**: `gcloud auth application-default login`

---

## Verification

```bash
JSON_FILE=~/.pb-reports/mcp-raw-YYYY-MM-DD.json
FILE_SIZE=$(stat -f%z "$JSON_FILE" 2>/dev/null || stat -c%s "$JSON_FILE")
[[ $FILE_SIZE -lt 10000 ]] && echo "ERROR: Too small" && exit 1
echo "OK: $FILE_SIZE bytes"
```

---

## Failure Actions

| Issue | Action |
|-------|--------|
| BigQuery auth fails | `gcloud auth application-default login` |
| Gemini CLI fails | Check `GEMINI_API_KEY` env |
| File < 10KB | Check BigQuery data |
| Validation fails | Check for placeholders |
| Day-of-week wrong | Run fix_day_of_week.py |

---

*Last updated: 2026-01-26 | v7.1 | MCP deprecated, Python only*
