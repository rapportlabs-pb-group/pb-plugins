# Templates (v6.3)

> **Canonical Reference**: `1765097238.258199`
> **Last Updated**: 2026-01-06

---

## ⚠️ pb_intel_report JSON → Markdown 변환 (Notion용)

`pb_intel_report.parts[0].text`는 **JSON 문자열**입니다.
이 JSON을 아래 형식으로 **Markdown 변환**해야 Notion에서 읽을 수 있습니다.

### 변환 매핑 테이블

| JSON Path | Markdown Output |
|-----------|-----------------|
| `title` | `# PB 데일리 인텔리전스 브리핑` |
| `headline` | `**헤드라인**: {value}` + `---` |
| `summary.section_title` | `## 📊 전체 PB 요약` |
| `summary.yesterday_performance` | `### 어제 성과` + `<table>` |
| `summary.exposure_share` | `### 노출 점유율 변화` + `<table>` |
| `summary.weekly_trend` | `### 주간 추세` + `<table>` |
| `brand_snapshot.section_title` | `## 📈 브랜드별 스냅샷` |
| `brand_snapshot.table[]` | 9개 브랜드 `<table>` (시즌 코호트 컬럼 포함) |
| `season_cohort` | `## 📦 시즌 품번별 판매 비중` + `<table>` (7컬럼: 구분/시즌/거래액/비중/상품수/노출수/SPV) |
| `top_performers.section_title` | `## 🚀 Top Performers (어제 성과)` |
| `top_performers.mvp` | `### MVP: {brand_name}` + bullet list |
| `top_performers.rising_star` | `### Rising Star: {brand_name}` + bullet list |
| `urgent_priorities.section_title` | `## 🚨 Urgent Priorities (어제 성과)` |
| `urgent_priorities.gmv_decline` | `### GMV 하락: {brand_name}` + bullet list |
| `urgent_priorities.efficiency_decline` | `### 효율 하락: {brand_name}` + bullet list |
| `urgent_action_products.section_title` | `## ⚠️ 조치가 필요한 상품 (어제 기준)` |
| `urgent_action_products.products[]` | `<table>` |
| `missed_opportunities.section_title` | `## 💡 Missed Opportunities (어제자 기준)` |
| `missed_opportunities.segment` | 텍스트 블록 |
| `top_10_growing_products.section_title` | `## 🔥 Top 10 급성장 상품 (어제 기준, 전주 대비 +30% 이상)` |
| `top_10_growing_products.products[]` | `<table>` |
| `action_items[]` | `## 🎯 Today's Action Items` + 번호 목록 |

### ⚠️ CRITICAL: Notion 테이블 필수 형식 (v6.4)

**테이블은 다음 2가지 규칙을 반드시 준수!**

1. `<table>` 태그에 **속성 없이** 사용 (❌ `header-row="true"` 사용 금지)
2. 각 `<td>` 요소를 **별도 줄**에 배치

```html
<table>
<tr>
<td>헤더1</td>
<td>헤더2</td>
<td>헤더3</td>
</tr>
<tr>
<td>값1</td>
<td>값2</td>
<td>값3</td>
</tr>
</table>
```

| 규칙 | 필수 | 설명 |
|------|------|------|
| `<table>` 속성 없음 | ✅ 필수 | `header-row="true"` 사용 시 행이 column으로 병합됨 |
| `<td>` 별도 줄 | ✅ 필수 | 인라인 배치 시 렌더링 오류 발생 |

**❌ FORBIDDEN**:
- `header-row="true"` 속성 → 행이 column으로 이상하게 병합됨
- `<tr><td>A</td><td>B</td></tr>` 인라인 배치 → 렌더링 오류
- `:---` 구분선 행 → Notion HTML 테이블에서 보이는 행으로 렌더링됨

---

### 브랜드별 스냅샷 테이블 (9개 브랜드)

```html
<table>
<tr>
<td>브랜드</td>
<td>어제 GMV (등락)</td>
<td>어제 SPV</td>
<td>GMV 비중</td>
<td>노출 비중</td>
<td>노출 점유율 (기획전/MD/개인화)</td>
<td>채널 비중 (개인화/광고/기획전/검색)</td>
<td>시즌 코호트 (신상/재진행/1년차+)</td>
</tr>
<tr>
<td>노어</td>
<td>5,055,063 (43.7%)</td>
<td>16.94</td>
<td>0.3%</td>
<td>0.4%</td>
<td>기획전 0.6% / MD 0.2% / 개인화 0.3%</td>
<td>개인화 24.86% / 광고 27.40% / 기획전 33.82% / 검색 7.20%</td>
<td>신상 65.2% (SPV 12.5) / 재진행 8.0% (SPV 8.3) / 1년차+ 26.8% (SPV 15.2)</td>
</tr>
... (9개 브랜드 모두 동일 형식)
</table>
```

### 시즌 품번별 판매 비중 테이블 (7컬럼)

```html
<table>
<tr>
<td>구분</td>
<td>시즌</td>
<td>거래액</td>
<td>비중</td>
<td>상품수</td>
<td>노출수</td>
<td>SPV</td>
</tr>
<tr>
<td>0년차 신상</td>
<td>FW</td>
<td>12,345,678</td>
<td>28.5%</td>
<td>42</td>
<td>1,234,567</td>
<td>10.00</td>
</tr>
<tr>
<td>0년차 신상</td>
<td>SS</td>
<td>5,678,901</td>
<td>13.1%</td>
<td>18</td>
<td>567,890</td>
<td>10.00</td>
</tr>
<tr>
<td>0년차 재진행</td>
<td>FW</td>
<td>3,456,789</td>
<td>8.0%</td>
<td>25</td>
<td>456,789</td>
<td>7.57</td>
</tr>
<tr>
<td>0년차 재진행</td>
<td>SS</td>
<td>1,234,567</td>
<td>2.9%</td>
<td>10</td>
<td>234,567</td>
<td>5.26</td>
</tr>
<tr>
<td>1년차 이상</td>
<td>-</td>
<td>20,567,890</td>
<td>47.5%</td>
<td>156</td>
<td>2,345,678</td>
<td>8.77</td>
</tr>
</table>
```

---

### 변환 예시

**JSON Input:**
```json
{
  "title": "PB 데일리 인텔리전스 브리핑",
  "headline": "퀸즈셀렉션(+94.89%)과 노어(+49.78%)의 급성장세가...",
  "summary": {
    "section_title": "📊 전체 PB 요약",
    "yesterday_performance": {
      "gmv_y": "31,975,215",
      "gmv_wow_same_day_growth": "-4.28%",
      ...
    }
  }
}
```

**Markdown Output:**
```markdown
# PB 데일리 인텔리전스 브리핑
**헤드라인**: 퀸즈셀렉션(+94.89%)과 노어(+49.78%)의 급성장세가...
---
## 📊 전체 PB 요약
### 어제 성과
- **GMV**: 31,980,000원 (-4.28% 🧊)
- **SPV**: 12.43 (+5.20% 🔥)
- **GMV 비중**: 2.15%
- **노출 비중**: 3.50%
- **MD2대비 SPV비중**: 85.3%
### 노출 점유율
- **기획전**: 1.80% (-0.50p 🔽)
- **MD 추천**: 18.00% (-2.00p 🔽)
- **개인화**: 2.50% (+0.30p 🔥)
```

**참고**: 요약 섹션은 bullet list 형식 사용, 테이블은 브랜드별 스냅샷/Top 10 등에 사용

### 단위 변환

| Metric | JSON Value | Display |
|--------|------------|---------|
| GMV | `31975215` 또는 `"31,975,215"` | `31.98백만` |
| SPV | `12.43` | `12.43` (원 생략 가능) |
| Growth | `-4.28%` | `-4.28% 🧊` |

**Emoji 규칙**: 양수 → 🔥 / 음수 → 🧊 또는 🔽

---

## portfolio_stage_briefing (Notion용)

`portfolio_stage_briefing.parts[0].text`는 **이미 Markdown**입니다.
**변환 없이 그대로** Notion에 추가합니다.

```markdown
# 📑 PB 포트폴리오 데일리 전략 브리핑 (2024년 X월 X일)
## 🚀 PB 포트폴리오 데일리 전략 브리핑 (두괄식 요약)
...
```

---

## Slack 메인 브리핑 템플릿

### ⚠️ Top Performers 데이터 소스 규칙 (v7.5)

| 섹션 | 데이터 소스 | 수준 |
|------|------------|------|
| MVP 헤더 | `brand_snapshot` → GMV 성장률 1위 브랜드 | 브랜드 |
| Top Performers | `brand_snapshot` → GMV 성장률 상위 3개 브랜드 | 브랜드 |
| Top Performers 견인 상품 | `top_10_growing_products` → 해당 브랜드의 대표 상품 | 상품 |
| 주요 상품 TOP 3 | `top_10_growing_products` → 상위 3개 상품 | 상품 |

**⚠️ Top Performers에서 상품 성장률을 브랜드 성장률처럼 표시하면 안 됨!**
- `brand_snapshot`의 `yesterday_gmv` 괄호 안 성장률 = 브랜드 GMV 성장률
- `top_10_growing_products`의 `gmv_wow_same_day_growth` = 상품 성장률

```
:newspaper: *PB 데일리 인텔리전스 브리핑* ({YYYY-MM-DD} ({요일}))
━━━━━━━━━━━━━━━━━━━━
*PB GMV {±성장률}%* {이모지} | *MVP: {브랜드} {±브랜드_성장률}%* {이모지}
━━━━━━━━━━━━━━━━━━━━

:bar_chart: *전체 PB 성과*
• 어제: GMV *{값}백만* ({±성장률}% {이모지}), SPV *{값}원* ({±성장률}% {이모지}) | 거래액비중: {비중}% | MD2대비 SPV비중: {비율}%
• 주간: GMV *{값}백만* ({±성장률}% {이모지}), SPV {값}원
• 채널: 기획전 *{%}%* | 개인화 *{%}%* | 광고 *{%}%* | 검색 *{%}%* | 기타 *{%}%*
• 코호트: 신상 *{%}%* | 재진행 *{%}%* | 1년차+ *{%}%*

:rocket: *Top Performers* (브랜드 어제 GMV)
• *{브랜드}* GMV {값}백만 (*{±브랜드_성장률}%* {이모지}) - {대표_상품명}({±상품_성장률}%) 견인
• *{브랜드}* GMV {값}백만 (*{±브랜드_성장률}%* {이모지}) - {대표_상품명}({±상품_성장률}%) 견인
• *{브랜드}* GMV {값}백만 (*{±브랜드_성장률}%* {이모지}) - {대표_상품명}({±상품_성장률}%) 견인

*주요 상품 TOP 3*
:first_place_medal: {상품명} ({브랜드}) - GMV *{±성장률}%* | {값}백만
:second_place_medal: {상품명} ({브랜드}) - GMV *{±성장률}%* | {값}백만
:third_place_medal: {상품명} ({브랜드}) - GMV *{±성장률}%* | {값}백만

:rotating_light: *Urgent Priorities*
• :exclamation: {문제유형} | *{브랜드} {±성장률}%* {이모지} - {원인 및 조치}
• :exclamation: {문제유형} | *{브랜드} {±성장률}%* {이모지} - {원인 및 조치}

:clipboard: 상세분석: <{Notion_URL}|Notion> | <{Looker_URL}|Looker Studio>
<!subteam^<YOUR_SLACK_SUBTEAM_ID>>
```

---

## Slack 브랜드 스레드 템플릿 (9개 필수)

```
{브랜드명} {이모지}
• 어제: GMV {값}백만 {±성장률}% {이모지}, SPV {값}원
• 주간: GMV {값}백만 {±%}% {이모지}, SPV {값}원
• 노출: 기획전 {%}%, MD부스트 {%}%, 개인화 {%}%
• 코호트: 신상 {%}% (SPV {값}) | 재진행 {%}% (SPV {값}) | 1년차+ {%}% (SPV {값})
```

**예시 - 성장 브랜드:**
```
브에트와 :fire:
• 어제: GMV 0.63백만 +226.82% :fire:, SPV 32.06원
• 주간: GMV 6.56백만 +15.3% :fire:, SPV 28.50원
• 노출: 기획전 0.02%, MD부스트 0.10%, 개인화 0.03%
• 코호트: 신상 45.2% (SPV 35.1) | 재진행 22.0% (SPV 28.3) | 1년차+ 32.8% (SPV 25.6)
```

**예시 - 하락 브랜드:**
```
퀸즈셀렉션 :ice_cube:
• 어제: GMV 0.99백만 -23.42% :ice_cube:, SPV 9.74원
• 주간: GMV 4.23백만 -8.5% :ice_cube:, SPV 10.20원
• 노출: 기획전 0.10%, MD부스트 0.41%, 개인화 0.14%
• 코호트: 신상 30.1% (SPV 11.2) | 재진행 18.5% (SPV 8.9) | 1년차+ 51.4% (SPV 9.5)
```

---

## 9개 브랜드 목록 (순서 고정)

1. 노어
2. 다나앤페타
3. 마치마라
4. 베르다
5. 브에트와
6. 아르앙
7. 지재
8. 퀸즈셀렉션
9. 희애

---

## Formatting Rules

### 이모지 규칙

| Condition | Emoji |
|-----------|-------|
| 성장률 > 0% | `:fire:` |
| 성장률 ≤ 0% | `:ice_cube:` |

### 필수 요소

| Element | Format |
|---------|--------|
| 헤더 | `:newspaper: PB 데일리 인텔리전스 브리핑 ({날짜} ({요일}))` |
| 구분선 | `━━━━━━━━━━━━━━━━━━━━` (헤더 아래, MVP 아래) |
| MVP 라인 | `PB GMV {±성장률}% {이모지} \| MVP: {브랜드} {±성장률}% {이모지}` |
| 채널 노출 | `• 채널: 기획전 *{%}%* \| 개인화 *{%}%* \| 광고 *{%}%* \| 검색 *{%}%* \| 기타 *{%}%*` |
| 섹션 이모지 | `:bar_chart:`, `:rocket:`, `:rotating_light:`, `:clipboard:` |
| 메달 | `:first_place_medal:`, `:second_place_medal:`, `:third_place_medal:` |
| Urgent | `:exclamation:` |
| 불릿 | `•` (유니코드) |
| 구분자 | `\|` (값 구분), `,` (항목 내 구분) |
| 괄호 | `()` (날짜, 브랜드, 성장률에 사용) |
| 성장률 부호 | `+` (양수), `-` (음수) |
| 링크 | `<URL\|Text>` 형식 (Notion, Looker Studio) |
| content_type | `text/plain` 필수 (하이퍼링크 정상 작동) |
| 그룹 태그 | `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` (메시지 맨 끝) |

### 채널 노출 매핑 (channel_exposure_yesterday)

| JSON Key | 한글명 | 표시 순서 |
|----------|--------|-----------|
| `collection_share` | 기획전 | 1 |
| `personalized_share` | 개인화 | 2 |
| `ad_share` | 광고 | 3 |
| `search_share` | 검색 | 4 |
| `etc_share` | 기타 | 5 (md+best+branding+etc 합산 또는 etc만) |

**Note**: 주요 4개 채널(기획전/개인화/광고/검색)을 강조, 나머지는 기타로 합산하거나 생략 가능

### 가독성 개선 (v6.2)

| Element | Format |
|---------|--------|
| 헤더/섹션명 | `*text*` 볼드 처리 |
| 핵심 수치 | `*값*` 볼드 처리 |
| 섹션 간격 | 빈 줄 1개 추가 |

### FORBIDDEN (금지)

| Pattern | Reason |
|---------|--------|
| `_italic_` | 사용 안함 |
| `**bold**` | Slack은 `*text*` 사용 |
| 🥇🥈🥉 Unicode | `:first_place_medal:` 등 코드 사용 |
| `subteam<YOUR_SLACK_SUBTEAM_ID>` | `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` 형식 필수 |
| URL 직접 노출 | `<URL\|Text>` 링크 형식 사용 |

---

## 검증 체크리스트

### 메인 메시지
- [ ] `:newspaper:` 헤더로 시작 (날짜/요일 괄호 안에)
- [ ] `━━━━` 구분선 2개 (헤더 아래, MVP 아래)
- [ ] MVP 라인 존재 (PB GMV + `|` + MVP 브랜드)
- [ ] 성장률에 `+`/`-` 부호 포함
- [ ] `:bar_chart: 전체 PB 성과` 섹션 (`|` 구분자 사용)
- [ ] **⚠️ `거래액비중: {%}%` 포함** (어제 라인, validation `summary.gmv_share` 또는 mcp-raw `summary.share.GMV`)
- [ ] **⚠️ `MD2대비 SPV비중: {%}%` 포함** (어제 라인, validation `summary.spv_vs_md2` 또는 mcp-raw `summary.share.SPV_vs_MD2`)
- [ ] **채널 노출 라인 존재** (기획전/개인화/광고/검색/기타 5개 채널)
- [ ] `:rocket: Top Performers (브랜드 어제 GMV)` - **브랜드 레벨 성장률** (brand_snapshot 기준)
- [ ] **⚠️ Top Performers 성장률 ≠ 주요 상품 성장률** (브랜드 vs 상품 구분 확인)
- [ ] `주요 상품 TOP 3` (메달 이모지, 브랜드 괄호 안에, `|` 구분)
- [ ] `:rotating_light: Urgent Priorities` (`:exclamation:`, `|` 구분)
- [ ] `:clipboard: 상세분석:` 링크 (`<URL|Text>` 형식)
- [ ] `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` 맨 끝에 위치

### 브랜드 스레드
- [ ] 9개 브랜드 모두 발송
- [ ] 각 스레드 `{브랜드명} {이모지}` 형식
- [ ] `• 어제:`, `• 주간:`, `• 노출:`, `• 코호트:` 4줄 구조

---

## Notion 관련

**Notion 콘텐츠는 MCP 도구에서 반환된 데이터를 그대로 사용합니다.**

- `mcp__Pb_daily_report_mcp__daily_report_maker` → `pb_intel_report` + `portfolio_stage_briefing`
- MCP raw 파일: `~/.pb-reports/mcp-raw-{YYYY-MM-DD}.json`
- 별도 템플릿 변환 없이 MCP 응답을 Notion에 직접 저장

---

*Last updated: 2026-01-06 | v6.3 | Based on thread 1765097238.258199*
