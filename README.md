# PB Plugins Marketplace

라포랩스 Pb 그룹의 Claude Code 플러그인 마켓플레이스입니다.

## 사용 방법

### 1. 마켓플레이스 추가

```bash
/plugin marketplace add rapportlabs-pb-group/pb-plugins
```

### 2. 플러그인 설치

```bash
# 사용 가능한 플러그인 목록 확인
/plugin

# 특정 플러그인 설치
/plugin install <plugin-name>@pb-plugins
```

### 3. 플러그인 사용

```bash
/<plugin-name>:<command>
```

## 플러그인 개발 가이드

### 새 플러그인 만들기

1. `plugins/` 폴더에 새 플러그인 폴더 생성
2. 아래 구조로 파일 생성:

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json       # 필수: 플러그인 메타데이터
├── commands/             # 슬래시 명령어
│   └── main.md
└── README.md
```

3. plugin.json 작성:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "플러그인 설명",
  "author": {"name": "작성자명"},
  "commands": ["./commands/"]
}
```

4. `.claude-plugin/marketplace.json`에 플러그인 등록:

```json
{
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./plugins/my-plugin",
      "description": "플러그인 설명",
      "version": "1.0.0"
    }
  ]
}
```

5. PR 생성 → 리뷰 → 머지

### 주의사항

- 경로는 `${CLAUDE_PLUGIN_ROOT}` 변수 사용
- CLAUDE.md 파일 포함 금지
- credentials, .env 등 민감 파일 포함 금지

## 플러그인 목록

| 플러그인 | 설명 | 버전 |
|---------|------|-----|
| example-plugin | 예제 플러그인 | 1.0.0 |
| plugin-maker | Create, secure, and publish Claude Code plugins to PB marketplace | 2.3.0 |

## 문의

Issues 탭에서 문의해주세요.