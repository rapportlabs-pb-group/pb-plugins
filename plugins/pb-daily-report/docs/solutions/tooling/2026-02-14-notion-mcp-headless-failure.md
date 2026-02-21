# Notion MCP Unavailable in Headless Claude Sessions

## Problem
When `pb-run-all-v7.2.sh` runs via launchd (headless), Claude CLI session
reports "I don't have Notion MCP tools available in this session." Step 1
(BigQuery + Gemini) succeeds but Steps 2 (Notion) and 3 (Slack) fail.

## Root Cause
Notion MCP plugin (`mcp__plugin_Notion_notion__*`) is loaded as a user-interactive
plugin that requires browser-based OAuth. In headless/launchd sessions, the plugin
is not initialized because there is no interactive session to complete authentication.

## Solution
1. **Immediate**: Added Slack error notification (v7.3) to alert on failures
   via channel `<YOUR_SLACK_ERROR_CHANNEL_ID>`, so failures are noticed immediately
2. **Manual recovery**: Open interactive Claude session, connect Notion MCP
   via `/mcp`, then run Steps 2+3 manually
3. **Long-term**: Investigate Notion API token-based auth instead of OAuth
   plugin to enable fully headless operation

## Prevention
- Monitor `<YOUR_SLACK_ERROR_CHANNEL_ID>` Slack channel for automation failure alerts
- If Notion MCP auth expires, re-authenticate in an interactive session
  before the next launchd run

## Tags
notion, mcp, headless, launchd, automation, oauth
