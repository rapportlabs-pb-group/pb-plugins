# Changelog

## [7.5.1] - 2026-02-21

- Automated PB (Private Brand) daily intelligence briefing system. BigQuery + Gemini CLI + Claude Code pipeline that generates daily performance reports and distributes via Notion and Slack.


## [7.5.1] - 2026-02-21

- Automated PB (Private Brand) daily intelligence briefing system. BigQuery + Gemini CLI + Claude Code pipeline that generates daily performance reports and distributes via Notion and Slack.


## [task] - 2026-02-12 11:49

- **Item**: Exception handling refinement (narrow `except Exception`) — 4 cases narrowed in scripts/
- **Phase**: General
- **Source**: auto

All notable changes to PB Daily Report will be documented in this file.

## [v7.2] - 2026-01-27

### Added
- Gemini raw markdown format support in converters
- Date rule documentation: `analysis_date = execution_date - 1`
- Troubleshooting guide entries #7, #8, #9
- PLAN.md for milestone tracking
- CHANGELOG.md (this file)
- `.ruff.toml` linter configuration
- Milestone hooks in `.claude/settings.local.json`

### Changed
- Timeout recommendation: 5 min → 10 min (script uses 25 min)
- Automation script updated to v7.2 (`pb-run-all-v7.2.sh`)
- Variable naming: `TODAY/YESTERDAY` → `EXECUTION_DATE/ANALYSIS_DATE`
- **Code consolidation**: Duplicate functions → `pb_utils.py`
  - `get_korean_day_of_week` (was in 3 files)
  - `extract_date_from_filename` (was in 3 files)

### Fixed
- `AttributeError: 'str' object has no attribute 'items'` when Gemini returns raw markdown
- Date off-by-one error in Notion/Slack output

## [v7.1] - 2026-01-26

### Changed
- MCP tools deprecated - Python scripts only
- n8n/Docker dependencies removed
- Workflow: `report_generator.py` → `fix_day_of_week.py` → `convert_mcp_to_notion.py`

### Added
- `converters/` module (v2.0) for JSON→Markdown transformation
- `scripts/` module for BigQuery + Gemini integration

## [v7.0] - 2026-01-26

### Added
- Python-based report generator (`report_generator.py`)
- BigQuery client with parallel query execution
- Gemini CLI subprocess wrapper

### Removed
- MCP `daily_report_maker` tool dependency

## [v6.5] - 2026-01-25

### Fixed
- Notion content missing fields issue
- `convert_mcp_to_notion.py` script created

## [v6.4] - 2026-01-24

### Fixed
- Day-of-week off by one error
- `fix_day_of_week.py` script added

---

*Format based on [Keep a Changelog](https://keepachangelog.com/)*
