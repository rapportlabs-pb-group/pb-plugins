# PB Daily Report - Automation Guide v7.1

> 자동화 설정 가이드 - 2026-01-26 최신화

## v7.1 주요 변경 (2026-01-26)

| 항목 | 이전 | 현재 |
|------|------|------|
| n8n/Docker 체크 | 있음 | **제거됨** |
| AUTH_TOKEN | 필요 | **제거됨** |
| report_generator.py 확인 | 없음 | **추가됨** |
| MCP 의존성 | 있음 | **제거됨** |

---

## Current Setup (v7.1)

Daily 11:00 AM KST automatic execution via macOS LaunchAgent.

### Key Files

| File | Purpose |
|------|---------|
| `~/bin/pb-run-all-v7.0.sh` | Execution script (v7.1) |
| `~/Library/LaunchAgents/kr.rapportlabs.pb-daily.plist` | Schedule config |
| `~/Library/Logs/pb-daily-v7.out.log` | stdout log |
| `~/Library/Logs/pb-daily-v7.err.log` | stderr log |

### v7.1 Key Features

- **MCP 완전 제거** - Python 스크립트만 사용
- Slash command direct use (`/pb-run-all ${TODAY}`)
- Slash command = Single Source of Truth
- report_generator.py 존재 확인 (사전 검증)
- 25 min timeout (`gtimeout 1500`)
- 100 max turns (`--max-turns 100`)
- Permission bypass (`--permission-mode bypassPermissions`)
- stdin redirect (`</dev/null`) - ensures non-interactive mode

### 워크플로우

```
LaunchAgent (11:00 KST)
       │
       ▼
pb-run-all-v7.0.sh
       │
       ├─ 환경 변수 설정 (PATH, TZ, LANG)
       ├─ report_generator.py 존재 확인
       │
       ▼
Claude CLI (/pb-run-all)
       │
       ├─ report_generator.py (BigQuery + Gemini)
       ├─ fix_day_of_week.py
       ├─ validate_mcp_raw.py
       ├─ convert_mcp_to_notion.py
       ├─ Notion 페이지 생성
       └─ Slack 발송
```

---

## LaunchAgent Management

```bash
# Reload after changes
launchctl unload ~/Library/LaunchAgents/kr.rapportlabs.pb-daily.plist
launchctl load ~/Library/LaunchAgents/kr.rapportlabs.pb-daily.plist

# Check status
launchctl list | grep pb-daily

# Manual trigger
launchctl start kr.rapportlabs.pb-daily

# View logs
tail -f ~/Library/Logs/pb-daily-v7.out.log
```

---

## Script Execution Command (v7.1)

```bash
PROMPT="/pb-run-all ${TODAY}"

gtimeout 1500 claude \
    -p "$PROMPT" \
    --permission-mode bypassPermissions \
    --max-turns 100 \
    </dev/null
```

---

## Environment Variables (v7.1)

| Variable | Value | Purpose |
|----------|-------|---------|
| HOME | ~ | User home |
| PATH | ~/.npm-global/bin:/opt/homebrew/bin:... | CLI paths |
| TZ | Asia/Seoul | Timezone |
| LANG | ko_KR.UTF-8 | Locale |

**제거됨**: `AUTH_TOKEN` (MCP 인증용 - 더 이상 필요 없음)

---

## Pre-flight Checks (v7.1)

스크립트 실행 전 자동 확인:

```bash
# 1. Claude CLI 확인
[ -f "claude" ]

# 2. gtimeout 확인
[ -f "gtimeout" ]

# 3. report_generator.py 확인 (v7.1 신규)
[ -f "$HOME/.pb-reports/scripts/report_generator.py" ]
```

---

## Version History Summary

| Version | Change | Issue Fixed |
|---------|--------|-------------|
| **v7.1** | MCP 제거, Python only | MCP 불안정성 해결 |
| v7.3 | TODAY parameter | Date calculation bug |
| v7.2 | Slash cmd direct | Maintenance complexity |
| v7.0 | Direct prompt | Turn exhaustion |

---

## pmset Configuration

```bash
# Wake Mac at 10:58 AM for 11:00 execution
sudo pmset repeat wake MTWRFSU 10:58:00
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| BigQuery 인증 실패 | `gcloud auth application-default login` |
| Gemini CLI 타임아웃 | 네트워크 확인, 재시도 |
| report_generator.py not found | `~/.pb-reports/scripts/` 확인 |
| 타임아웃 (25분 초과) | 로그 확인, 개별 단계 수동 실행 |

---

## Related Documentation

- **[SYSTEM_DOCUMENTATION.md](./SYSTEM_DOCUMENTATION.md)** - 종합 시스템 문서
- **[workflow.md](./workflow.md)** - 워크플로우 가이드
- **[troubleshooting.md](./troubleshooting.md)** - 문제 해결

---

*Last updated: 2026-01-26 | v7.1 | MCP deprecated, Python only*
