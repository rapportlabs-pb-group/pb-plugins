# 플러그인 개발 가이드

## 플러그인 구조

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json       # 필수: 플러그인 메타데이터
├── commands/             # 필수: 슬래시 명령어
│   ├── main.md
│   └── sub-command.md
├── agents/               # 선택: 커스텀 에이전트
│   └── my-agent.md
├── rules/                # 선택: 프로젝트 규칙
│   └── coding-style.md
├── hooks/                # 선택: 이벤트 훅
│   └── pre-commit.sh
└── README.md             # 필수: 사용 설명서
```

## plugin.json 스펙

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "description": "플러그인 설명 (한 줄)",
  "author": {
    "name": "작성자명",
    "email": "email@example.com"
  },
  "commands": ["./commands/"],
  "agents": ["./agents/"],
  "rules": ["./rules/"],
  "hooks": {
    "pre-commit": "./hooks/pre-commit.sh"
  },
  "keywords": ["keyword1", "keyword2"],
  "dependencies": [],
  "requirements": {
    "claude-code": ">=1.0.0"
  }
}
```

## 명령어 파일 작성

### Frontmatter

```yaml
---
description: "명령어 설명 (자동완성에 표시됨)"
argument-hint: "<required> [optional]"
---
```

### 본문

마크다운으로 Claude에게 전달할 지시사항 작성

```markdown
# Command Name

## Context
이 명령어가 하는 일 설명

## Instructions
1. 단계별 지시사항
2. ...

## Output Format
예상 출력 형식
```

## 경로 변수

플러그인 내에서 사용 가능한 변수:

| 변수 | 설명 |
|------|------|
| `${CLAUDE_PLUGIN_ROOT}` | 플러그인 루트 디렉토리 |
| `${CLAUDE_PROJECT_ROOT}` | 현재 프로젝트 루트 |

## 금지 사항

- ❌ `CLAUDE.md` 파일 포함
- ❌ `.env`, `credentials.json` 등 민감 정보
- ❌ 하드코딩된 절대 경로
- ❌ 외부 API 키 직접 포함

## 테스트 방법

```bash
# 로컬 플러그인 설치
/plugin install ./plugins/my-plugin

# 명령어 테스트
/my-plugin:main
```
