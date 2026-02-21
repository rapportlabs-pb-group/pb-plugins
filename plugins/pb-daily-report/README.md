# PB Daily Report

Automated Private Brand (PB) daily intelligence briefing system for e-commerce portfolio management.

## Overview

Generates daily PB performance reports by querying BigQuery, analyzing with Gemini CLI, and distributing via Notion and Slack.

**Pipeline**: BigQuery → Gemini CLI → JSON → Notion → Slack

## Installation

### Prerequisites

- Python 3.10+
- Google Cloud SDK (`gcloud auth application-default login`)
- Gemini CLI (`GEMINI_API_KEY` env var)
- Claude Code CLI

### Setup

```bash
# Scripts are installed at ~/.pb-reports/
# Claude commands at .claude/commands/
cd <project-root>
claude
/pb-run-all
```

## Usage

### Full Workflow (recommended)

```
/pb-run-all
```

Runs all 3 steps: Data Generation → Notion → Slack

### Individual Steps

| Step | Command | Description |
|------|---------|-------------|
| 1 | `/pb-report-generate` | BigQuery + Gemini report generation |
| 2 | `/pb-notion-create` | Notion page creation |
| 3 | `/pb-slack-send` | Slack distribution (main + 9 brand threads) |

### Validation

```
/pb-validate
```

## Architecture

```
~/.pb-reports/
├── scripts/           # Core pipeline (report_generator.py, bigquery_client.py, etc.)
├── converters/        # JSON→Markdown conversion (base.py, sections.py)
├── sql/               # BigQuery queries (pb_portfolio_v7.7.sql, pb_dashboard_v2.0.sql)
├── prompts/           # Gemini prompts (intel_briefing.txt, strategy_briefing.txt)
├── convert_mcp_to_notion.py
├── fix_day_of_week.py
└── validate_mcp_raw.py
```

## 9 Monitored Brands

노어, 다나앤페타, 마치마라, 베르다, 브에트와, 아르앙, 지재, 퀸즈셀렉션, 희애

## Documentation

- [System Documentation](docs/SYSTEM_DOCUMENTATION.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Notion Format](docs/notion-format.md)
- [Slack Templates](.claude/commands/_references/templates.md)
