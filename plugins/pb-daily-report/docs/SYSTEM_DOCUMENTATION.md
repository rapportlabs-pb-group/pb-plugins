# PB Daily Report System Documentation v7.4

> 종합 시스템 문서 - 2026-02-02 최신화

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [아키텍처](#2-아키텍처)
3. [데이터 흐름](#3-데이터-흐름)
4. [스크립트 및 도구](#4-스크립트-및-도구)
5. [명령어 (Slash Commands)](#5-명령어-slash-commands)
6. [설정 (Configuration)](#6-설정-configuration)
7. [템플릿](#7-템플릿)
8. [검증 규칙](#8-검증-규칙)
9. [자동화](#9-자동화)
10. [문제 해결](#10-문제-해결)
11. [버전 히스토리](#11-버전-히스토리)

---

## 1. 시스템 개요

### 1.1 목적

PB(Private Brand) 일일 성과 데이터를 자동으로 수집, 분석, 발행하는 시스템입니다.

- **데이터 소스**: BigQuery + Gemini CLI (Python 스크립트)
- **발행 채널**: Notion 데이터베이스 + Slack 채널
- **실행 방식**: Claude Code CLI + macOS LaunchAgent

### 1.2 v7.1 주요 변경 (2026-01-26)

| 항목 | 이전 (v6.5) | 현재 (v7.1) |
|------|-------------|-------------|
| 데이터 소스 | MCP 서버 | **BigQuery + Gemini CLI** |
| 의존성 | n8n Docker + MCP | **Python 스크립트만** |
| Step 1 | MCP daily_report_maker | **report_generator.py** |

**⚠️ MCP 도구 사용 금지**: `daily_report_maker`, `daily_report_maker_2` 사용하지 않음

### 1.3 Quick Start

```bash
cd <project-root>
claude
/pb-run-all
```

**결과**: 3-5분 후 Notion 페이지 생성 + Slack 브리핑 완료

### 1.4 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **SSOT** | Single Source of Truth - 각 단계는 지정된 파일만 참조 |
| **결정론적 변환** | Python 스크립트로 JSON→Markdown 변환 (수동 변환 금지) |
| **검증 우선** | 발송 전 모든 데이터 검증 필수 |

---

## 2. 아키텍처

### 2.1 디렉토리 구조

```
~/.pb-reports/                       ← 데이터 저장소 + 스크립트
├── scripts/                         ← Python 모듈 (v7.1 신규)
│   ├── __init__.py
│   ├── config.py                    ← 환경 설정
│   ├── bigquery_client.py           ← BigQuery 병렬 쿼리
│   ├── gemini_headless.py           ← Gemini CLI subprocess
│   ├── data_processor.py            ← 데이터 직렬화 + 프롬프트 + weekly_brand_data 추출
│   └── report_generator.py          ← 메인 CLI 오케스트레이터
├── sql/                             ← SQL 쿼리 (v7.1 신규)
│   ├── pb_portfolio_v7.7.sql        ← PB 포트폴리오 쿼리
│   └── pb_dashboard_v2.0.sql        ← 대시보드 쿼리
├── prompts/                         ← Gemini 프롬프트 (v7.1 신규)
│   ├── intel_briefing.txt           ← Intel Briefing
│   └── strategy_briefing.txt        ← Strategy Briefing
├── convert_mcp_to_notion.py         ← JSON→Markdown 변환
├── fix_day_of_week.py               ← 요일 수정
├── validate_mcp_raw.py              ← 검증
├── mcp-raw-YYYY-MM-DD.json          ← Step 1 출력
├── notion-content-YYYY-MM-DD.md     ← Step 2 입력
└── validation-YYYY-MM-DD.json       ← Step 3 입력

<project-root>/
├── CLAUDE.md                        ← Claude Code 설정
├── .claude/commands/
│   ├── pb-run-all.md                ← 전체 워크플로우 (v7.1)
│   ├── pb-report-generate.md        ← Step 1 (v7.1)
│   ├── pb-notion-create.md          ← Step 2
│   ├── pb-slack-send.md             ← Step 3
│   └── pb-validate.md               ← 시스템 검증
└── docs/
    ├── SYSTEM_DOCUMENTATION.md      ← 이 문서
    ├── workflow.md                  ← 워크플로우 가이드
    ├── automation.md                ← 자동화 설정
    └── troubleshooting.md           ← 문제 해결
```

### 2.2 기술 스택 (v7.1)

| 컴포넌트 | 기술 |
|----------|------|
| CLI | Claude Code (Anthropic) |
| 데이터 | BigQuery (google-cloud-bigquery) |
| AI 생성 | Gemini CLI (subprocess) |
| Notion | `mcp__plugin_Notion_notion` |
| Slack | `mcp__slack` |
| 자동화 | macOS LaunchAgent |
| 스크립트 | Python 3.9+ |

### 2.3 제거된 의존성 (v7.1)

| 컴포넌트 | 상태 |
|----------|------|
| n8n Docker | ❌ 불필요 |
| MCP 서버 | ❌ 불필요 |
| AUTH_TOKEN | ❌ 불필요 |

---

## 3. 데이터 흐름

### 3.1 전체 흐름도 (v7.1)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PB Daily Report v7.1                          │
└─────────────────────────────────────────────────────────────────────────┘

Step 1: Data Generation (Python)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    BigQuery
        │ (병렬 쿼리)
        ├─────────────────┐
        ▼                 ▼
    pb_portfolio      pb_dashboard
    v7.7.sql          v2.0.sql
        │                 │
        ▼                 ▼
    Gemini CLI        Gemini CLI
        │                 │
        ▼                 ▼
    pb_intel_report   portfolio_stage_briefing
        │                 │
        └────────┬────────┘
                 ▼
    mcp-raw-YYYY-MM-DD.json
                 │
                 ▼
    fix_day_of_week.py → validate_mcp_raw.py

Step 2: Notion Page Creation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    mcp-raw-YYYY-MM-DD.json
        │
        ▼ (⚠️ MANDATORY)
    convert_mcp_to_notion.py ◄──── Python datetime (요일 계산)
        │
        ▼
    notion-content-YYYY-MM-DD.md
        │
        ▼ (notion-create-pages)
    Notion Database
        │
        ▼ (검증 + 저장)
    validation-YYYY-MM-DD.json ──► fix_day_of_week.py

Step 3: Slack Distribution
━━━━━━━━━━━━━━━━━━━━━━━━━━━
    validation-YYYY-MM-DD.json
        │
        ▼ (⚠️ templates.md 먼저 Read)
    Main Briefing (1 메시지)
        │
        ▼ (thread_ts)
    Brand Threads (9 메시지)
        │
        ▼
    Slack Channel (#pb-daily)
```

### 3.2 SSOT 규칙

| Step | 데이터 소스 | 사용 금지 |
|------|-------------|-----------|
| Step 1 | BigQuery + Gemini (Python) | ~~MCP 도구~~ |
| Step 2 | `mcp-raw-*.json` (파일) | 메모리, raw JSON 직접 저장 |
| Step 2.1 | `convert_mcp_to_notion.py` 출력 | 수동 JSON→Markdown 변환 |
| Step 3 | `validation-*.json` | Notion 재조회, MCP 재호출 |

### 3.3 데이터 리니지

```
BigQuery → Gemini CLI → mcp-raw.json → convert_mcp_to_notion.py → notion-content.md → Notion → validation.json → Slack
```

---

## 4. 스크립트 및 도구

### 4.1 report_generator.py (v7.1 신규)

**목적**: BigQuery 데이터 조회 + Gemini CLI로 리포트 생성

**위치**: `~/.pb-reports/scripts/report_generator.py`

**사용법**:
```bash
# 어제 날짜로 생성
python3 ~/.pb-reports/scripts/report_generator.py

# 특정 날짜 지정
python3 ~/.pb-reports/scripts/report_generator.py 2026-01-25
```

**출력**: `~/.pb-reports/mcp-raw-YYYY-MM-DD.json`

**내부 동작**:
```python
1. BigQuery 병렬 쿼리 (ThreadPoolExecutor)
   ├─ pb_portfolio_v7.7.sql → portfolio_data
   └─ pb_dashboard_v2.0.sql → dashboard_data

2. Gemini CLI 호출 (subprocess)
   ├─ gemini -y "$INTEL_PROMPT" → pb_intel_report
   └─ gemini -y "$STRATEGY_PROMPT" → portfolio_stage_briefing

3. MCP-compatible JSON 출력
   └─ metadata에 weekly_brand_data + season_cohort_data 포함
```

### 4.2 convert_mcp_to_notion.py

**목적**: MCP raw JSON을 Notion Markdown으로 결정론적 변환

**위치**: `~/.pb-reports/convert_mcp_to_notion.py`

**사용법**:
```bash
python3 ~/.pb-reports/convert_mcp_to_notion.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
```

**출력**: `~/.pb-reports/notion-content-YYYY-MM-DD.md`

**처리 섹션** (9개):
1. `headline` - 헤드라인
2. `summary_pb` - 전체 PB 요약
3. `brand_snapshot` - 브랜드별 스냅샷 (9개)
4. `top_performers` - MVP/Rising Star
5. `urgent_priorities` - 긴급 우선순위
6. `urgent_action_products` - 조치 필요 상품
7. `missed_opportunities` - 놓친 기회
8. `top_growing_products` - Top 10 급성장 상품
9. `action_items` - 액션 아이템

**v7.1 업데이트**: Gemini 출력 형식 자동 감지
- 리스트 형식 (`[{type, name, metrics, diagnosis}]`) 지원
- 다양한 키 이름 매핑 (`brand` ↔ `brand_name` 등)

### 4.3 fix_day_of_week.py

**목적**: 요일 오류 수정

**사용법**:
```bash
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/validation-YYYY-MM-DD.json
```

### 4.4 validate_mcp_raw.py

**목적**: MCP 원본 데이터 무결성 검증

**사용법**:
```bash
python3 ~/.pb-reports/validate_mcp_raw.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
```

---

## 5. 명령어 (Slash Commands)

### 5.1 명령어 목록

| 명령어 | 설명 | 소요 시간 |
|--------|------|-----------|
| `/pb-run-all` | 전체 워크플로우 (1→2→3) | 3-5분 |
| `/pb-report-generate` | Step 1: Python 데이터 생성 | 1-2분 |
| `/pb-notion-create` | Step 2: Notion 페이지 생성 | 1-2분 |
| `/pb-slack-send` | Step 3: Slack 발송 | 30초-1분 |
| `/pb-validate` | 시스템 상태 확인 | 10초 |

### 5.2 /pb-run-all (v7.1)

**체크리스트**:
- [ ] **`report_generator.py` 실행** (BigQuery + Gemini)
- [ ] `fix_day_of_week.py` 실행
- [ ] `validate_mcp_raw.py` 실행
- [ ] **⚠️ `convert_mcp_to_notion.py` 실행** (수동 변환 금지)
- [ ] **변환 검증 리포트 확인**
- [ ] **⚠️ 요일은 Python datetime으로 계산**
- [ ] Notion `ancestor-path` 확인
- [ ] `validation-*.json` 저장
- [ ] **⚠️ `fix_day_of_week.py` 실행** (validation 파일)
- [ ] **⚠️ `_references/templates.md` Read 필수** (Step 3 전)
- [ ] **`content_type: text/plain`** (Step 3)
- [ ] **9개 브랜드 스레드 발송**

---

## 6. 설정 (Configuration)

### 6.1 BigQuery 설정 (v7.1 신규)

| 항목 | 값 |
|------|-----|
| Project ID | `<YOUR_BIGQUERY_PROJECT_ID>` |
| 인증 | Application Default Credentials |

### 6.2 Gemini 설정 (v7.1 신규)

| 항목 | 값 |
|------|-----|
| CLI | `gemini` (npm global) |
| 타임아웃 | 180초 |
| 모드 | `-y` (YOLO mode) |

### 6.3 Notion 설정

| 항목 | 값 |
|------|-----|
| Database ID | `<YOUR_NOTION_DATABASE_ID>` |
| Data Source ID | `<YOUR_NOTION_DATASOURCE_ID>` |

### 6.4 Slack 설정

| 항목 | 값 |
|------|-----|
| Channel ID | `<YOUR_SLACK_CHANNEL_ID>` |
| Group Tag | `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` |

### 6.5 브랜드 목록

**9개 브랜드** (순서 고정):
노어, 다나앤페타, 마치마라, 베르다, 브에트와, 아르앙, 지재, 퀸즈셀렉션, 희애

**금지 브랜드**:
오드리나, 더블유온, 에일린, 헨리, 오르시, 로이드

---

## 7. 템플릿

### 7.1 Slack 브랜드 스레드 (v7.3 - 4줄 구조)

```
{브랜드명} {이모지}
• 어제: GMV {값}백만 {±성장률}% {이모지}, SPV {값}원
• 주간: GMV {값}백만 {±%}% {이모지}, SPV {값}원
• 노출: 기획전 {%}%, MD부스트 {%}%, 개인화 {%}%
• 코호트: 신상 {%}% (SPV {값}) | 재진행 {%}% (SPV {값}) | 1년차+ {%}% (SPV {값})
```

### 7.2 Slack 메인 브리핑 코호트 라인 (v7.3)

```
• 코호트: 신상 *{%}%* | 재진행 *{%}%* | 1년차+ *{%}%*
```

### 7.3 주간 데이터 소스 (v7.3)

| 데이터 | metadata 키 | 출처 |
|--------|-------------|------|
| GMV L7D (주간 거래액) | `weekly_brand_data[].gmv_l7d` | `report_level == '02. Summary by Brand'` |
| GMV WoW growth | `weekly_brand_data[].gmv_wow_growth` | `report_level == '02. Summary by Brand'` |
| SPV L7D | `weekly_brand_data[].spv_l7d` | `report_level == '02. Summary by Brand'` |
| SPV WoW growth | `weekly_brand_data[].spv_wow_growth` | `report_level == '02. Summary by Brand'` |
| 시즌 코호트 | `season_cohort_data` | `pb_season_cohort_v1.0.sql` |

---

## 8. 검증 규칙

(기존 v6.5와 동일 - 생략)

---

## 9. 자동화

### 9.1 LaunchAgent 설정 (v7.1)

**스케줄**: 매일 오전 11:00 KST

**주요 파일**:
| 파일 | 용도 |
|------|------|
| `~/bin/pb-run-all-v7.0.sh` | 실행 스크립트 (v7.1) |
| `~/Library/LaunchAgents/kr.rapportlabs.pb-daily.plist` | 스케줄 설정 |
| `~/Library/Logs/pb-daily-v7.out.log` | stdout 로그 |
| `~/Library/Logs/pb-daily-v7.err.log` | stderr 로그 |

### 9.2 v7.1 변경사항

| 항목 | 이전 | 현재 |
|------|------|------|
| n8n/Docker 체크 | 있음 | **제거됨** |
| AUTH_TOKEN | 필요 | **제거됨** |
| report_generator.py 확인 | 없음 | **추가됨** |

### 9.3 실행 명령

```bash
PROMPT="/pb-run-all ${TODAY}"

gtimeout 1500 claude \
    -p "$PROMPT" \
    --permission-mode bypassPermissions \
    --max-turns 100 \
    </dev/null
```

### 9.4 LaunchAgent 관리

```bash
# 재로드
launchctl unload ~/Library/LaunchAgents/kr.rapportlabs.pb-daily.plist
launchctl load ~/Library/LaunchAgents/kr.rapportlabs.pb-daily.plist

# 상태 확인
launchctl list | grep pb-daily

# 수동 실행
launchctl start kr.rapportlabs.pb-daily

# 로그 확인
tail -f ~/Library/Logs/pb-daily-v7.out.log
```

---

## 10. 문제 해결

### 10.1 주요 이슈 및 해결

| 이슈 | 증상 | 해결 |
|------|------|------|
| BigQuery 인증 실패 | 쿼리 에러 | `gcloud auth application-default login` |
| Gemini CLI 타임아웃 | 180초 초과 | 네트워크 확인, 재시도 |
| 요일 밀림 | 일요일 → 토요일 | `fix_day_of_week.py` 실행 |
| Notion 필드 누락 | 섹션 없음 | `convert_mcp_to_notion.py` 실행 |
| Slack 환각 | 없는 데이터 | `validation-*.json`만 사용 |

### 10.2 검증 명령어

```bash
# Output 파일 확인
ls -la ~/.pb-reports/mcp-raw-$(date -v-1d '+%Y-%m-%d').json

# 데이터 검증
python3 ~/.pb-reports/validate_mcp_raw.py ~/.pb-reports/mcp-raw-*.json

# 요일 수정
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/mcp-raw-*.json

# 자동화 로그 확인
tail -100 ~/Library/Logs/pb-daily-v7.out.log
```

---

## 11. 버전 히스토리

| 버전 | 날짜 | 주요 변경 |
|------|------|-----------|
| **v7.4** | 2026-02-03 | MD2대비 SPV비중 추가 (Slack/Notion), 주간 GMV 금액 표시, gmv_l7d 파이프라인 추가 |
| v7.3 | 2026-02-02 | 주간 브랜드 데이터 파이프라인, Slack 4줄 브랜드 스레드, 코호트 라인 |
| v7.2 | 2026-01-27 | 날짜 규칙 명확화, Gemini raw markdown 지원 |
| **v7.1** | 2026-01-26 | **MCP 완전 제거**, Python 스크립트만 사용 (BigQuery + Gemini CLI) |
| v7.0 | 2026-01-26 | n8n → Python 마이그레이션 시작 |
| v6.5 | 2026-01-14 | `convert_mcp_to_notion.py` 스크립트 추가 |
| v6.4 | 2026-01-12 | Python datetime으로 요일 계산 강제 |
| v6.3 | 2026-01-06 | Notion 테이블 형식 규칙 추가 |

---

## 부록 A: Critical Rules 요약

| Step | 규칙 | 위반 시 |
|------|------|---------|
| **전체** | **MCP 도구 사용 금지** | 워크플로우 실패 |
| Step 1 | `report_generator.py` 실행 | 데이터 없음 |
| Step 1 | `fix_day_of_week.py` 실행 필수 | 요일 오류 |
| Step 2 | **`convert_mcp_to_notion.py` 실행 필수** | 필드 누락 |
| Step 2 | **Python datetime으로 요일 계산** | 하루 밀림 |
| Step 3 | **`templates.md` 먼저 Read** | 템플릿 불일치 |
| Step 3 | `content_type: text/plain` | 링크/멘션 깨짐 |
| Step 3 | 9개 브랜드 스레드 필수 (4줄 구조) | 워크플로우 실패 |

---

*Last updated: 2026-02-03 | v7.4 | MD2대비 SPV비중 추가, 주간 GMV 금액 표시, gmv_l7d 파이프라인*
