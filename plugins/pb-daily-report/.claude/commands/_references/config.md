# PB Daily Report Configuration

## Notion
| Key | Value |
|-----|-------|
| Database ID | `<YOUR_NOTION_DATABASE_ID>` |
| Data Source ID | `<YOUR_NOTION_DATASOURCE_ID>` |
| Property Name | `이름` (Korean, NOT "Title") |

## Slack
| Key | Value |
|-----|-------|
| Channel ID | `<YOUR_SLACK_CHANNEL_ID>` |
| Group Tag | `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` |
| Bot | `<YOUR_SLACK_BOT_NAME>` |

## External Links
| Name | URL |
|------|-----|
| Looker Studio | `https://lookerstudio.google.com/u/1/reporting/<YOUR_LOOKER_REPORT_ID>/page/p_68mmtt2ovd` |

## File Paths
| Purpose | Path |
|---------|------|
| MCP Raw | `~/.pb-reports/mcp-raw-YYYY-MM-DD.json` |
| Validation JSON | `~/.pb-reports/validation-YYYY-MM-DD.json` |
| Validation Script | `~/.pb-reports/validate_mcp_raw.py` |

## Brands (9 Total)
노어, 다나앤페타, 마치마라, 베르다, 브에트와, 아르앙, 지재, 퀸즈셀렉션, 희애

## Forbidden Brands
오드리나, 더블유온, 에일린, 헨리, 오르시, 로이드

## Date Calculation
```python
from datetime import datetime
analysis_date = execution_date - 1 day
korean_days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
day_name = korean_days[analysis_date.weekday()]
```

## Units
| Metric | Unit | Example |
|--------|------|---------|
| GMV | 백만원 | 49.7백만 (NOT 억) |
| SPV | 원 | 15.00원 |
| Growth | % | +8.86% |
| Share | % | 2.15% |
