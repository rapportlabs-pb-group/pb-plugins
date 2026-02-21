# PB Daily Report - Slack Templates

> **Canonical Source**: `.claude/commands/_references/templates.md`
> **Reference Message**: `1765097238.258199` (2025-12-06 토요일)

## Quick Reference

### Main Briefing Structure (v7.3)
```
:newspaper: *PB 데일리 인텔리전스 브리핑* ({날짜} ({요일}))
━━━━━━━━━━━━━━━━━━━━
*PB GMV {±%}* {이모지} | *MVP: {브랜드} {±%}* {이모지}
━━━━━━━━━━━━━━━━━━━━

:bar_chart: *전체 PB 성과*
(빈 줄)
:rocket: *Top Performers*
(빈 줄)
*주요 상품 TOP 3*
(빈 줄)
:rotating_light: *Urgent Priorities*
(빈 줄)
:clipboard: 상세분석: <URL|Notion> | <URL|Looker Studio>
<!subteam^<YOUR_SLACK_SUBTEAM_ID>>
```

### Brand Thread Structure (9개 필수, v7.3 4줄)
```
{브랜드명} {이모지}
• 어제: GMV {값}백만 {±%} {이모지}, SPV {값}원
• 주간: GMV {값}백만 {±%}% {이모지}, SPV {값}원
• 노출: 기획전 {%}%, MD부스트 {%}%, 개인화 {%}%
• 코호트: 신상 {%}% (SPV {값}) | 재진행 {%}% (SPV {값}) | 1년차+ {%}% (SPV {값})
```

## Key Rules

| DO | DON'T |
|----|-------|
| `*text*` 볼드 | `**bold**` 마크다운 |
| 섹션 간 빈 줄 | 빈 줄 없음 |
| `━━━━` 구분선 | 구분선 없음 |
| `\|` 구분자 | 구분자 없음 |
| `({날짜} ({요일}))` | `{날짜} {요일}` |
| `+X%` / `-X%` 부호 | `X%` 부호 없음 |
| `<URL\|Text>` 링크 | URL 직접 노출 |
| `•` bullet | `- ` hyphen |
| `content_type: text/plain` | `text/markdown` (링크 깨짐) |
| `:first_place_medal:` | 🥇 Unicode |
| `<!subteam^<YOUR_SLACK_SUBTEAM_ID>>` | `subteam<YOUR_SLACK_SUBTEAM_ID>` |
| `:fire:` / `:ice_cube:` | Other emojis |

## Required Counts

- **9 brand threads** (ALL required)
- **`:first_place_medal:` `:second_place_medal:` `:third_place_medal:`** for TOP 3
- **`:exclamation:`** for Urgent items
- **Group tag** at message END

## 9 Brands (Fixed Order)

노어, 다나앤페타, 마치마라, 베르다, 브에트와, 아르앙, 지재, 퀸즈셀렉션, 희애

## Full Details

See `.claude/commands/_references/templates.md` for complete templates and validation checklist.

---
*Last updated: 2026-02-02 | v7.3 | 4줄 브랜드 스레드, 코호트 라인 추가*
