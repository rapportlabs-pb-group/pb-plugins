# PB Daily Report - Troubleshooting Guide v7.2

> 문제 해결 가이드 - 2026-01-27 최신화

## Quick Diagnostics

```bash
# MCP connection check
claude mcp list

# System validation
/pb-validate
```

## Common Issues

### 1. Slack Hallucination (Solved v5.7)
**Symptom**: Fake brands/products/numbers in Slack
**Cause**: Step 3 executed without fetching Notion data
**Fix**: Always fetch Notion page before Slack step

### 2. Notion Private Page (Solved v5.10)
**Symptom**: Page not visible in database
**Check**: `ancestor-path` is empty when fetched
**Fix**: Include `parent` parameter with data_source_id

### 3. MCP Data Corruption (Solved v5.16)
**Symptom**: Placeholder strings in output
**Cause**: heredoc used instead of Write tool
**Fix**: MUST use Write tool for MCP raw save
**Verify**: Run `validate_mcp_raw.py`

### 4. Automation Turn Exhaustion (Solved v7.0)
**Symptom**: LaunchAgent exits with no output (42s)
**Cause**: Slash commands consume turns
**Fix**: Use direct prompt instead of `/pb-run-all`
**Script**: `~/bin/pb-run-all-v7.0.sh`

### 5. Day-of-Week Off by One (Solved v6.4)
**Symptom**: Report shows wrong day (e.g., Sunday → Saturday)
**Cause**: Claude model infers day-of-week incorrectly (one day off)
**Check**: Compare `report_day` in validation JSON with actual date
**Fix**: Run `fix_day_of_week.py` after MCP save and after validation save
```bash
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/validation-YYYY-MM-DD.json
```
**Prevention**: Always use Python datetime for day calculation:
```bash
python3 -c "from datetime import datetime; d=datetime(YYYY,MM,DD); days=['월요일','화요일','수요일','목요일','금요일','토요일','일요일']; print(days[d.weekday()])"
```

### 6. Notion Content Missing Fields (Solved v6.5)
**Symptom**: Notion page missing sections (channel_exposure, missed_opportunities, top 10 products, etc.)
**Cause**: Manual JSON→Markdown conversion by Claude causes field omission
**Check**: Compare Notion page content with MCP raw JSON
**Fix**: Use `convert_mcp_to_notion.py` script instead of manual conversion
```bash
python3 ~/.pb-reports/convert_mcp_to_notion.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
```
**Prevention**: NEVER manually convert JSON→Markdown. Always use the script.
**Verification**: Check conversion report shows all 12 sections with ✓

### 7. Gemini Raw Markdown Format Error (Solved v7.2)
**Symptom**: `AttributeError: 'str' object has no attribute 'items'`
**Cause**: Gemini returns `daily_intelligence_briefing` as full markdown string instead of structured JSON
**Check**: Inspect `pb_intel_report.parts[0].text` - if it contains markdown directly
**Fix**: Update converters to handle raw markdown format:
```python
# converters/base.py - parse_pb_intel_report()
if isinstance(dib, str):
    return {'_raw_markdown': dib}
```
**Files Modified**:
- `~/.pb-reports/converters/base.py` (v2.1)
- `~/.pb-reports/converters/sections.py` (v2.1)
- `~/.pb-reports/convert_mcp_to_notion.py` (v2.1)

### 8. Date Off by One Day (Solved v7.2)
**Symptom**: Report shows execution_date instead of analysis_date (e.g., Jan 27 instead of Jan 26)
**Cause**: Misunderstanding of date rule - analysis_date = execution_date - 1
**Check**:
```bash
# If executed on 2026-01-27, analysis_date should be 2026-01-26
python3 -c "from datetime import datetime, timedelta; exec_date=datetime(2026,1,27); print(f'Execution: {exec_date:%Y-%m-%d}'); print(f'Analysis: {(exec_date-timedelta(days=1)):%Y-%m-%d}')"
```
**Fix**:
- Run `report_generator.py` without date argument (auto-calculates yesterday)
- Or ensure passed date is execution_date, not analysis_date
**Rule**: `analysis_date = execution_date - 1 day`

### 9. Automation Timeout (Solved v7.2)
**Symptom**: LaunchAgent times out before completion
**Cause**: 5-minute timeout too short for BigQuery + Gemini
**Check**: `tail -50 ~/Library/Logs/pb-daily-v7.err.log`
**Fix**: Increase timeout to 10 minutes (600000ms)
```bash
# In pb-run-all script or Bash command
gtimeout 600 python3 ~/.pb-reports/scripts/report_generator.py
```

### 10. Numerical Mismatch (Solved v5.12)
**Symptom**: Slack numbers differ from Notion
**Cause**: Data from memory/cache instead of Notion
**Fix**: Step 2.6 validates all numbers before Slack

## Verification Commands

```bash
# MCP raw file check
ls -la ~/.pb-reports/mcp-raw-$(date -v-1d '+%Y-%m-%d').json

# Validate MCP data integrity
python3 ~/.pb-reports/validate_mcp_raw.py ~/.pb-reports/mcp-raw-*.json

# Fix day-of-week in MCP raw file
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/mcp-raw-*.json

# Check validation file day-of-week
python3 -c "import json; d=json.load(open('$HOME/.pb-reports/validation-$(date -v-1d '+%Y-%m-%d').json')); print(f\"Date: {d['report_date']}, Day: {d['report_day']}\")"

# Check automation logs
tail -100 ~/Library/Logs/pb-daily-v7.out.log
tail -50 ~/Library/Logs/pb-daily-v7.err.log
```

## Anti-Hallucination Checklist

Before Step 3 (Slack):
- [ ] Notion page fetched via `mcp__notionMCP__notion-fetch`
- [ ] 9 brands verified from Notion
- [ ] All GMV/SPV values match Notion exactly
- [ ] TOP 3 products exist in Notion TOP 10
- [ ] No invented brands (오드리나, 더블유온, 에일린, 헨리, 오르시, 로이드)

## Data Source Rules

| Allowed | Forbidden |
|---------|-----------|
| Notion page fetch | Claude memory |
| MCP raw file | Session history |
| Current MCP response | Pattern learning |

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | None |
| 1 | Validation failed | Check MCP raw file |
| 124 | Timeout | Increase timeout or check MCP |
| 127 | Command not found | Check PATH |

---

## Related Documentation

- **[SYSTEM_DOCUMENTATION.md](./SYSTEM_DOCUMENTATION.md)** - 종합 시스템 문서
- **[workflow.md](./workflow.md)** - 워크플로우 가이드
- **[automation.md](./automation.md)** - 자동화 설정

---

*Last updated: 2026-01-27 | v7.2 | Added Gemini raw markdown, date rule, timeout issues*
