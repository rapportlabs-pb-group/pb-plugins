---
allowed-tools: Bash(claude mcp list:*), Bash(cat:*), Read
description: Validate PB Daily Report system status and connections
---

# PB Daily Report - System Validation

Check the health and status of the PB Daily Report system, including MCP connections and recent execution history.

## Validation Checks

### 1. MCP Connection Status
!`claude mcp list`

### 2. Required MCP Servers Check
Verify these essential MCP servers are connected:
- ✅ `mcp__Pb_daily_report_mcp` - Primary report generator
- ✅ `mcp__notionMCP` - Notion integration
- ✅ `mcp__slack` - Slack messaging

### 3. Last Successful Execution
!`cat .stamps/last_success.date 2>/dev/null || echo "No recent success recorded"`

### 4. System Files Status
!`ls -la .claude/commands/pb-*.md 2>/dev/null | wc -l`

### 5. Configuration Validation
Check key configuration values:
- **Notion Data Source ID**: `<YOUR_NOTION_DATASOURCE_ID>`
- **Slack Channel ID**: `<YOUR_SLACK_CHANNEL_ID>`
- **Group Tag**: `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>`

### 6. Workflow Integrity Checks (v5.11)
Critical validation gates in workflow:
- **Step 2.5**: Notion page verification (ancestor-path check)
- **Step 2.6**: Pre-Slack data validation gate (memory contamination prevention)
  - Prevents sending wrong-date data to Slack
  - Enforces current session data fetch before Step 3
  - Blocks memory contamination from previous sessions

## Available Commands
After validation, you can use:
- `/pb-run-all` - Execute complete workflow (includes Step 2.6 validation gate - v5.11)
- `/pb-report-generate` - Step 1 only
- `/pb-notion-create` - Step 2 only
- `/pb-slack-send` - Step 3 only (requires Step 2.6 completion - v5.11)

## Troubleshooting Quick Fixes

### MCP Connection Issues
```bash
claude mcp reconnect
```

### Individual MCP Server Issues
```bash
claude mcp restart mcp__Pb_daily_report_mcp
claude mcp restart mcp__notionMCP
claude mcp restart mcp__slack
```

### Fallback Options
- If primary MCP fails, use `mcp__Pb_daily_report_mcp__daily_report_maker_2`
- For connection issues, wait 30 seconds and retry
- Check network connectivity if all MCPs fail

## System Status Summary
Based on validation results:
- 🟢 **Ready**: All systems operational
- 🟡 **Caution**: Some issues detected, but workflow possible
- 🔴 **Failed**: Critical issues prevent execution

Use this command before running the daily workflow to ensure everything is working correctly.