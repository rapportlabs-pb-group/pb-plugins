---
allowed-tools: mcp__slack__conversations_add_message
description: Send Slack briefing and thread messages (Step 3) - v6.3
argument-hint: [notion_url] [briefing_content] [thread_data]
---

# PB Daily Report - Step 3: Slack Distribution v6.3

**References**:
- `_references/templates.md` - Message templates (based on `1765097238.258199`)
- `_references/config.md` - Channel ID, group tag

---

## ⚠️ CRITICAL API SETTINGS

```python
# 모든 Slack 메시지 발송 시 필수 파라미터
channel_id = "<YOUR_SLACK_CHANNEL_ID>"
content_type = "text/plain"  # ← 반드시 text/plain!
```

**`content_type: text/plain` 필수** - `text/markdown` 사용 시 링크/멘션 깨짐

---

## Pre-Flight Gate

```bash
JSON_FILE=~/.pb-reports/validation-YYYY-MM-DD.json
[[ ! -f "$JSON_FILE" ]] && echo "ERROR: JSON not found" && exit 1
```

**NO JSON = NO SEND**

---

## Message Validation (BEFORE sending)

### Main Message Checklist
- [ ] `:newspaper:` 헤더로 시작 (날짜/요일 괄호 안에)
- [ ] `━━━━` 구분선 2개 (헤더 아래, MVP 아래)
- [ ] MVP 라인: `*PB GMV {±%}%* {이모지} | *MVP: {브랜드} {±%}%* {이모지}`
- [ ] 성장률에 `+`/`-` 부호 포함
- [ ] `:bar_chart: *전체 PB 성과*` 섹션 (`|` 구분자 사용)
- [ ] **⚠️ `거래액비중: {%}%` 포함** (어제 라인 끝, `|` 구분)
- [ ] **⚠️ `MD2대비 SPV비중: {%}%` 포함** (어제 라인 끝, `|` 구분)
- [ ] `:rocket: *Top Performers* (브랜드 어제 GMV)` - **브랜드 레벨 성장률** (brand_snapshot 기준, 상품 성장률 금지)
- [ ] **⚠️ Top Performers 성장률 ≠ 주요 상품 성장률** (브랜드 vs 상품 구분 확인)
- [ ] `*주요 상품 TOP 3*` - `:first_place_medal:` 등, 브랜드 괄호 안에, `|` 구분
- [ ] `:rotating_light: *Urgent Priorities*` - `:exclamation:`, `|` 구분
- [ ] `:clipboard: 상세분석:` 링크 (`<URL|Text>` 형식)
- [ ] `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` 맨 끝에 위치

### Forbidden Patterns
- [ ] NO `_italic_` - 일반 텍스트 사용
- [ ] NO `**bold**` - Slack은 `*text*` 사용
- [ ] NO 🥇🥈🥉 Unicode - `:first_place_medal:` 등 사용
- [ ] NO `subteam<YOUR_SLACK_SUBTEAM_ID>` - `<!subteam^...>` 형식 필수
- [ ] NO URL 직접 노출 - `<URL|Text>` 링크 형식 필수
- [ ] NO `content_type: text/markdown` - 반드시 `text/plain`

### 9 Brand Threads (ALL REQUIRED)
- [ ] 노어, [ ] 다나앤페타, [ ] 마치마라
- [ ] 베르다, [ ] 브에트와, [ ] 아르앙
- [ ] 지재, [ ] 퀸즈셀렉션, [ ] 희애

**< 9개 = workflow failure**

---

## Sending Order

1. **Main briefing** → `<YOUR_SLACK_CHANNEL_ID>` → thread_ts 획득
2. **9 brand threads** → replies (use thread_ts from step 1)

---

## 📋 Main Message Template (v7.5)

### ⚠️ Top Performers = 브랜드 레벨 (CRITICAL)

| 섹션 | 데이터 소스 | 수준 |
|------|------------|------|
| MVP 헤더 | `brand_snapshot` → GMV 성장률 1위 브랜드 | 브랜드 |
| Top Performers | `brand_snapshot` → GMV 성장률 상위 3개 브랜드 | 브랜드 |
| Top Performers 견인 상품 | `top_10_growing_products` → 해당 브랜드의 대표 상품 | 상품 |
| 주요 상품 TOP 3 | `top_10_growing_products` → 상위 3개 상품 | 상품 |

**⚠️ 상품 성장률을 브랜드 성장률처럼 표시 금지!**

```
:newspaper: *PB 데일리 인텔리전스 브리핑* (YYYY-MM-DD (요일))
━━━━━━━━━━━━━━━━━━━━
*PB GMV {±성장률}%* {이모지} | *MVP: {브랜드} {±브랜드_성장률}%* {이모지}
━━━━━━━━━━━━━━━━━━━━

:bar_chart: *전체 PB 성과*
• 어제: GMV *{값}백만* ({±%}% {이모지}), SPV *{값}원* ({±%}% {이모지}) | 거래액비중: {%}% | MD2대비 SPV비중: {%}%
• 주간: GMV *{값}백만* ({±%}% {이모지}), SPV {값}원
• 코호트: 신상 *{%}%* | 재진행 *{%}%* | 1년차+ *{%}%*

:rocket: *Top Performers* (브랜드 어제 GMV)
• *{브랜드}* GMV {값}백만 (*{±브랜드_성장률}%* {이모지}) - {대표_상품명}({±상품_성장률}%) 견인
• *{브랜드}* GMV {값}백만 (*{±브랜드_성장률}%* {이모지}) - {대표_상품명}({±상품_성장률}%) 견인
• *{브랜드}* GMV {값}백만 (*{±브랜드_성장률}%* {이모지}) - {대표_상품명}({±상품_성장률}%) 견인

*주요 상품 TOP 3*
:first_place_medal: {상품명} ({브랜드}) - GMV *{±%}%* | {값}백만
:second_place_medal: {상품명} ({브랜드}) - GMV *{±%}%* | {값}백만
:third_place_medal: {상품명} ({브랜드}) - GMV *{±%}%* | {값}백만

:rotating_light: *Urgent Priorities*
• :exclamation: {문제유형} | *{브랜드} {±%}%* {이모지} - {원인 및 설명}
• :exclamation: {문제유형} | *{브랜드} {±%}%* {이모지} - {원인 및 설명}

:clipboard: 상세분석: <{Notion_URL}|Notion> | <{Looker_URL}|Looker Studio>
<!subteam^<YOUR_SLACK_SUBTEAM_ID>>
```

---

## 🔴 실제 예시 메시지 (복사용)

아래는 2026-02-11 데이터 기준 **정확한 형식**의 예시입니다:

```
:newspaper: *PB 데일리 인텔리전스 브리핑* (2026-02-11 (수요일))
━━━━━━━━━━━━━━━━━━━━
*PB GMV -19.0%* :ice_cube: | *MVP: 다나앤페타 +3.1%* :fire:
━━━━━━━━━━━━━━━━━━━━

:bar_chart: *전체 PB 성과*
• 어제: GMV *31.52백만* (-19.0% :ice_cube:), SPV *13.05원* (-7.6% :ice_cube:) | 거래액비중: 3.3% | MD2대비 SPV비중: 75.3%
• 주간: GMV *243.83백만* (-17.0% :ice_cube:), SPV 13.04원
• 채널: 기획전 *21.6%* | 개인화 *42.7%* | 광고 *14.43%* | 검색 *8.85%* | 기타 *8.1%*
• 코호트: 신상 *46.6%* | 재진행 *25.3%* | 1년차+ *28.1%*

:rocket: *Top Performers* (브랜드 어제 GMV)
• *다나앤페타* GMV 6.17백만 (*+3.1%* :fire:) - 셔츠 레이어드 니트 가디건(+189.7%) 견인
• *희애* GMV 1.23백만 (*+5.2%* :fire:) - 핸드메이드 울 코트(+42.3%) 견인
• *노어* GMV 2.45백만 (*-2.1%* :ice_cube:) - 볼드 체인 네크리스(+31.5%) 일부 상쇄

*주요 상품 TOP 3*
:first_place_medal: 셔츠 레이어드 니트 가디건 (다나앤페타) - GMV *+189.7%* | 0.50백만
:second_place_medal: 사선 버튼 카라넥 자수 포인트 니트 (마치마라) - GMV *+55.5%* | 0.38백만
:third_place_medal: 포근 울 래글런 버튼 니트 (다나앤페타) - GMV *+69.9%* | 0.29백만

:rotating_light: *Urgent Priorities*
• :exclamation: 성과 하락 | *지재 -25.3%* :ice_cube: - 기획전 노출 감소, SPV 하락으로 매력도 재검토 필요
• :exclamation: 효율 악화 | *마치마라 -14.6%* :ice_cube: - CTR 전주 대비 하락, 상품 구성 점검 필요

:clipboard: 상세분석: <https://www.notion.so/xxx|Notion> | <https://lookerstudio.google.com/u/1/reporting/<YOUR_LOOKER_REPORT_ID>/page/p_68mmtt2ovd|Looker Studio>
<!subteam^<YOUR_SLACK_SUBTEAM_ID>>
```

### 필수 체크 포인트 (발송 전 확인)

| # | 체크 항목 | 올바른 예 | 잘못된 예 |
|---|----------|----------|----------|
| 1 | 헤더 볼드 | `*PB 데일리...` | `PB 데일리...` |
| 2 | 구분선 | `━━━━━━━━━━` | (없음) |
| 3 | MVP 파이프 | `| *MVP:` | `MVP:` |
| 4 | 불릿 | `• 어제:` | ` 어제:` |
| 5 | 링크 형식 | `<URL|Text>` | `URL - Text` |
| 6 | 그룹 태그 | `<!subteam^S09...>` | `subteamS09...` |

---

## 📋 Brand Thread Template (9개 필수)

```
{브랜드명} {이모지}
• 어제: GMV {값}백만 {±성장률}% {이모지}, SPV {값}원
• 주간: GMV {값}백만 {±%}% {이모지}, SPV {값}원
• 노출: 기획전 {%}%, MD부스트 {%}%, 개인화 {%}%
• 코호트: 신상 {%}% (SPV {값}) | 재진행 {%}% (SPV {값}) | 1년차+ {%}% (SPV {값})
```

**스레드 데이터 소스**: validation JSON의 `brands` 배열 + MCP raw의 `exposure_share` + `weekly_brand_data` + `season_cohort_data`

### 브랜드 스레드 실제 예시

**성장 브랜드:**
```
다나앤페타 :fire:
• 어제: GMV 5.82백만 -15.7% :ice_cube:, SPV 12.50원
• 주간: GMV 8.45백만 +27.6% :fire:, SPV 11.80원
• 노출: 데이터 없음
• 코호트: 신상 42.1% (SPV 14.2) | 재진행 20.3% (SPV 10.5) | 1년차+ 37.6% (SPV 11.8)
```

**하락 브랜드:**
```
브에트와 :ice_cube:
• 어제: GMV 0.10백만 -74.1% :ice_cube:, SPV 10.00원
• 주간: GMV 0.35백만 -91.6% :ice_cube:, SPV 8.50원
• 노출: 데이터 없음
• 코호트: 신상 55.0% (SPV 12.3) | 재진행 15.0% (SPV 7.8) | 1년차+ 30.0% (SPV 9.1)
```

### 브랜드 스레드 체크리스트
- [ ] 모든 줄 앞에 `•` (유니코드 불릿) 있음
- [ ] 이모지는 WoW 기준으로 결정 (양수=:fire:, 음수=:ice_cube:)
- [ ] 어제/주간/노출/코호트 4줄 구조 유지

---

## Emoji Rules

| Condition | Emoji |
|-----------|-------|
| 성장률 > 0% | `:fire:` |
| 성장률 ≤ 0% | `:ice_cube:` |

---

## ⚠️ 거래액비중 / MD2대비 SPV비중 (CRITICAL - v7.4)

이 2개 지표는 **반드시** 메인 메시지 `어제:` 라인에 포함해야 합니다.

**데이터 소스** (fallback 순서):
1. validation JSON → `summary.gmv_share` / `summary.spv_vs_md2`
2. mcp-raw JSON → `pb_intel_report` 파싱 → `summary.share.GMV` / `summary.share.SPV_vs_MD2`

**Slack 출력 형식**:
```
• 어제: GMV *28.84백만* (-31.0% :ice_cube:), SPV *13.44원* (-14.6% :ice_cube:) | 거래액비중: 2.9% | MD2대비 SPV비중: 74.6%
```

**⚠️ 이 값이 없으면 메시지 발송 금지** - mcp-raw에서 직접 추출할 것

---

## ❌ COMMON MISTAKES

| Mistake | Correct |
|---------|---------|
| `content_type: text/markdown` | `content_type: text/plain` |
| `subteam<YOUR_SLACK_SUBTEAM_ID>` | `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` |
| `[링크텍스트](URL)` | `<URL\|링크텍스트>` |
| 스레드 4줄 미만 | 반드시 4줄 (어제/주간/노출/코호트) |
| 8개 이하 스레드 | 반드시 9개 브랜드 |
| 거래액비중 누락 | `summary.gmv_share` 또는 `summary.share.GMV` |
| MD2대비 SPV비중 누락 | `summary.spv_vs_md2` 또는 `summary.share.SPV_vs_MD2` |

---

## Example API Call

```python
mcp__slack__conversations_add_message(
    channel_id="<YOUR_SLACK_CHANNEL_ID>",
    content_type="text/plain",  # ← CRITICAL
    payload="..."
)
```
