# Skills Guide

> Generated: 2025-12-09
> Update this file when adding new skills to `~/.claude/skills/`

## Core Principle

**Before any action, ask: "Is there a skill for this?"**

Skills are reusable procedural knowledge. Using them ensures consistency, reduces token usage, and accumulates organizational knowledge.

## Available Skills (리오더 프로젝트용)

| Skill | When to Use |
|-------|-------------|
| `bigquery-schema-assistant` | BigQuery 테이블 스키마 조회, 쿼리 작성 시 |
| `collaborative-research-writing` | 데이터 분석 리포트 작성, 가설 검증 |
| `session-bridging` | 세션 시작/종료 시 progress.md 관리 |
| `systematic-debugging` | 쿼리 오류, 데이터 불일치 디버깅 |
| `statistical-analysis` | 예측 모델 검증, 백테스트 분석 |
| `notion-research-documentation` | 분석 결과 Notion 문서화 |
| `codex-collaboration` | 복잡한 아키텍처 결정, 다중 AI 검토 |

## Workflow

### 1. Check Before Acting

```
Action needed → Check this table → Invoke skill if found → Document usage
```

### 2. Document Skill Usage

When using a skill, note it briefly:
```markdown
Used: bigquery-schema-assistant - noir 테이블 스키마 확인
```

### 3. Session Continuity

For multi-session projects, use `session-bridging` skill:
- Session start: Check/create `progress.md`
- Session end: Update `progress.md`, commit clean state

## Project-Specific Skill Routing

| 작업 유형 | 추천 스킬 | 비고 |
|----------|----------|------|
| 새 브랜드 테이블 탐색 | `bigquery-schema-assistant` | 스키마 Notion DB 참조 |
| 예측 정확도 분석 | `statistical-analysis` | t-test, ANOVA 등 |
| 파라미터 튜닝 | `collaborative-research-writing` | 가설-검증 사이클 |
| 결과 문서화 | `notion-research-documentation` | AI 자료 페이지에 저장 |

## When NOT to Use Skills

- Single-task, quick fixes
- Highly context-specific one-offs
- Exploring new territory without patterns

## Adding New Skills

When you add a skill to `~/.claude/skills/`:
1. Update the table above
2. Add routing entry if applicable

---

*See `~/.claude/skills/[skill-name]/SKILL.md` for detailed skill documentation.*
