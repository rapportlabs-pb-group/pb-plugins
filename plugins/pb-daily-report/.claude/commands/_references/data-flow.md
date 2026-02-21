# Data Flow: MCP → Notion → Slack

## Overview

```
Step 1: MCP Call
    ↓
Step 1.2: Save to mcp-raw-YYYY-MM-DD.json (Write tool)
    ↓
Step 1.3: Validate MCP raw (validate_mcp_raw.py)
    ↓
Step 2: Create Notion page (from MCP file)
    ↓
Step 2.5: Verify Notion page (ancestor-path check)
    ↓
Step 2.6: Validate & Save to validation-YYYY-MM-DD.json
    ↓
Step 3: Send Slack (from validation JSON only)
```

---

## Step 1: MCP Data Generation

### MCP Tool Returns 2 Sections
| Section | Format | Use |
|---------|--------|-----|
| `pb_intel_report` | JSON | Notion + Slack |
| `portfolio_stage_briefing` | Markdown | Notion only |

### Date Hallucination Fix (v5.8.1)
MCP date fields are unreliable. Calculate:
```python
analysis_date = execution_date - 1 day
```

---

## Step 1.2: MCP Raw Storage (v5.16)

### Rules
- Use Write tool (NOT heredoc, NOT clipboard)
- Save COMPLETE response (no placeholders)
- File: `~/.pb-reports/mcp-raw-YYYY-MM-DD.json`

### Structure (v7.3)
```json
{
  "pb_intel_report": {"parts": [{"text": "..."}]},
  "portfolio_stage_briefing": {"parts": [{"text": "..."}]},
  "metadata": {
    "analysis_date": "YYYY-MM-DD",
    "execution_date": "YYYY-MM-DD",
    "season_cohort_data": [...],
    "weekly_brand_data": [
      {"brand_name": "노어", "gmv_wow_growth": 15.3, "spv_wow_growth": 5.2, "spv_l7d": 12.5},
      ...
    ]
  }
}
```

**v7.3 추가**: `weekly_brand_data` - `report_level == '02. Summary by Brand'`에서 추출한 브랜드별 주간 성장률

---

## Step 2: Notion Page Creation

### Data Source
Load from `~/.pb-reports/mcp-raw-YYYY-MM-DD.json` (NOT memory)

### Required Checks
1. Use `data_source_id` (NOT personal page)
2. Property name: `이름` (Korean)
3. Include both `pb_intel_report` + `portfolio_stage_briefing`

---

## Step 2.5: Notion Verification

### Pass Criteria
- `ancestor-path` NOT empty
- `properties` contains `이름`

### Fail Action
```
❌ STOP - Do not proceed to Step 3
Report: "Personal page created instead of database entry"
```

---

## Step 2.6: Pre-Slack Validation Gate (v5.13)

### Extract from Notion
- 9 brands with GMV, SPV, growth
- TOP 10 products (compare with MCP)
- Aggregate metrics

### Save to JSON
File: `~/.pb-reports/validation-YYYY-MM-DD.json`

```json
{
  "analysis_date": "YYYY-MM-DD",
  "notion_page_url": "https://...",
  "total_pb": {...},
  "brands": [...],  // 9 brands
  "top_products": [...],  // 10 products
  "urgent_items": [...]
}
```

---

## Step 3: Slack Distribution (v5.13)

### Data Source Rule
```
✅ ONLY: ~/.pb-reports/validation-YYYY-MM-DD.json
❌ NEVER: Notion fetch, MCP cache, memory, pattern guess
```

### Pre-Flight Checks
1. JSON file exists and non-empty
2. 9 brands present
3. 10 products present
4. All numerical values loaded

### Sending
1. Main briefing (1 message)
2. Brand threads (9 messages) - ALL required
3. Group tag at end

---

## SSOT Principle

| Step | Source | Never Use |
|------|--------|-----------|
| 2 | MCP raw file | Memory |
| 3 | Validation JSON | Notion re-fetch |

**Data lineage must be traceable: MCP → File → Notion → JSON → Slack**
