# PB Daily Report - Workflow Guide v7.1

> 워크플로우 가이드 - 2026-01-26 최신화

---

## v7.1 주요 변경 (2026-01-26)

| 항목 | 이전 (v6.5) | 현재 (v7.1) |
|------|-------------|-------------|
| Step 1 | MCP daily_report_maker | **report_generator.py** |
| 의존성 | n8n Docker + MCP | **Python 스크립트만** |
| 데이터 소스 | MCP 서버 | **BigQuery + Gemini CLI** |

**⚠️ MCP 도구 사용 금지**: `daily_report_maker`, `daily_report_maker_2` 사용하지 않음

---

## Quick Start

```bash
cd <project-root>
claude
/pb-run-all
```

**Result**: Complete report + Notion page + Slack briefing in 3-5 minutes

---

## Slash Commands

| Command | Purpose | Duration |
|---------|---------|----------|
| `/pb-run-all` | Full automated workflow | 3-5 min |
| `/pb-report-generate` | Step 1: Python 데이터 생성 | 1-2 min |
| `/pb-notion-create` | Step 2: Notion 페이지 생성 | 1-2 min |
| `/pb-slack-send` | Step 3: Slack 발송 | 30s-1 min |
| `/pb-validate` | System health check | 10s |

---

## v7.1 Command Structure

```
.claude/commands/
├── pb-run-all.md         ← 전체 워크플로우 (v7.1)
├── pb-slack-send.md      ← Step 3: Slack 발송
├── pb-notion-create.md   ← Step 2: Notion 생성
├── pb-report-generate.md ← Step 1: Python 데이터 (v7.1)
└── pb-validate.md        ← 시스템 검증

~/.pb-reports/
├── scripts/                    ← Python 모듈 (v7.1 신규)
│   ├── config.py
│   ├── bigquery_client.py
│   ├── gemini_headless.py
│   ├── data_processor.py
│   └── report_generator.py     ← 메인 CLI
├── sql/                        ← SQL 쿼리 (v7.1 신규)
│   ├── pb_portfolio_v7.7.sql
│   └── pb_dashboard_v2.0.sql
├── prompts/                    ← Gemini 프롬프트 (v7.1 신규)
│   ├── intel_briefing.txt
│   └── strategy_briefing.txt
├── convert_mcp_to_notion.py    ← JSON→Markdown 변환
├── fix_day_of_week.py          ← 요일 수정
└── validate_mcp_raw.py         ← 검증
```

---

## Workflow Steps

### Step 1: Data Generation (v7.1 - Python)

1. **Run `report_generator.py`** (BigQuery + Gemini)
   ```bash
   python3 ~/.pb-reports/scripts/report_generator.py [YYYY-MM-DD]
   ```

2. **Run `fix_day_of_week.py`** (요일 수정)
   ```bash
   python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
   ```

3. **Run `validate_mcp_raw.py`** (데이터 검증)
   ```bash
   python3 ~/.pb-reports/validate_mcp_raw.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
   ```

**출력**: `~/.pb-reports/mcp-raw-YYYY-MM-DD.json`

### Step 2: Notion Page Creation

1. **⚠️ Run `convert_mcp_to_notion.py`** (수동 변환 금지)
   ```bash
   python3 ~/.pb-reports/convert_mcp_to_notion.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
   ```

2. **검증 리포트 확인** (9섹션, 9브랜드, 10상품)

3. Load from `~/.pb-reports/notion-content-YYYY-MM-DD.md`

4. **⚠️ 요일은 Python datetime으로 계산** (Claude 추론 금지)
   ```bash
   python3 -c "from datetime import datetime; d=datetime(YYYY,MM,DD); days=['월요일','화요일','수요일','목요일','금요일','토요일','일요일']; print(f'{d:%Y-%m-%d} ({days[d.weekday()]})')"
   ```

5. Create page with `data_source_id`

6. Verify `ancestor-path` not empty

7. Save to `validation-{DATE}.json`

8. **⚠️ Run `fix_day_of_week.py`** on validation file

### Step 3: Slack Briefing

1. **⚠️ Read `_references/templates.md` first** (필수)

2. Load from `validation-{DATE}.json`

3. Build main message using exact template format

4. **Send with `content_type: text/plain`**

5. Get `thread_ts` from response

6. Send 9 brand threads (ALL required)

---

## Critical Rules (v7.1)

| Step | Rule | Violation Impact |
|------|------|------------------|
| **전체** | **MCP 도구 사용 금지** | 워크플로우 실패 |
| Step 1 | `report_generator.py` 실행 | 데이터 없음 |
| Step 2 | **`convert_mcp_to_notion.py` 실행 필수** | 필드 누락 |
| Step 2 | **Python datetime으로 요일 계산** | 하루 밀림 |
| Step 3 | **`templates.md` 먼저 Read** | 템플릿 불일치 |
| Step 3 | `content_type: text/plain` | 링크/멘션 깨짐 |

---

## Data Flow (SSOT)

```
BigQuery → Gemini CLI → mcp-raw.json → convert_mcp_to_notion.py → notion-content.md → Notion → validation.json → Slack
```

| Step | Source | Never Use |
|------|--------|-----------|
| Step 1 | BigQuery + Gemini (Python) | ~~MCP 도구~~ |
| Step 2 | mcp-raw-*.json (파일) | Memory |
| Step 2.1 | convert_mcp_to_notion.py 출력 | 수동 변환 |
| Step 3 | validation-*.json | Notion fetch |

---

## 9 Brands Required

노어, 다나앤페타, 마치마라, 베르다, 브에트와, 아르앙, 지재, 퀸즈셀렉션, 희애

**Forbidden**: 오드리나, 더블유온, 에일린, 헨리, 오르시, 로이드

---

## Tools Used (v7.1)

| Tool | Purpose |
|------|---------|
| `report_generator.py` | **Primary data source** (BigQuery + Gemini) |
| `mcp__plugin_Notion_notion__*` | Notion operations |
| `mcp__slack__*` | Slack messaging |

**⚠️ 사용 금지**:
- ~~`mcp__Pb_daily_report_mcp__daily_report_maker`~~
- ~~`mcp__Pb_daily_report_mcp__daily_report_maker_2`~~

---

## Configuration

| Item | Value |
|------|-------|
| BigQuery Project | `<YOUR_BIGQUERY_PROJECT_ID>` |
| Notion Data Source ID | `<YOUR_NOTION_DATASOURCE_ID>` |
| Slack Channel | `<YOUR_SLACK_CHANNEL_ID>` |
| Slack Group Tag | `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` |

---

## Related Documentation

- **[SYSTEM_DOCUMENTATION.md](./SYSTEM_DOCUMENTATION.md)** - 종합 시스템 문서
- **[automation.md](./automation.md)** - 자동화 설정
- **[troubleshooting.md](./troubleshooting.md)** - 문제 해결

---

*Last updated: 2026-01-26 | v7.1 | MCP deprecated, Python only (BigQuery + Gemini CLI)*
