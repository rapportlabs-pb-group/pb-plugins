# Contributing to PB Plugins

PB 플러그인 마켓플레이스에 기여하는 방법입니다.

## 새 플러그인 추가하기

### 1. 플러그인 개발

```bash
# pb-marketplace 스킬 사용 (권장)
/pb-marketplace:link ./my-plugin  # 로컬 테스트
/pb-marketplace:check             # 민감정보 검사
/pb-marketplace:upload            # 업로드
```

### 2. 수동으로 추가하기

1. 이 레포를 fork
2. `plugins/` 폴더에 플러그인 추가
3. `.claude-plugin/marketplace.json`에 플러그인 등록
4. PR 생성

## 플러그인 구조

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json       # 필수
├── commands/             # 슬래시 명령어
│   └── main.md
├── README.md             # 필수
└── CHANGELOG.md          # 권장
```

## plugin.json 필수 필드

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "플러그인 설명",
  "author": {
    "name": "작성자명"
  },
  "commands": ["./commands/"]
}
```

## 체크리스트

PR 전 확인사항:

- [ ] plugin.json 유효
- [ ] README.md 작성
- [ ] 민감정보 없음 (.env, *.key, API keys 등)
- [ ] CLAUDE.md 미포함
- [ ] 경로에 `${CLAUDE_PLUGIN_ROOT}` 사용

## 코드 리뷰

- 모든 PR은 CODEOWNERS의 승인 필요
- marketplace.json 변경은 관리자 승인 필요
- 민감정보 포함 시 즉시 거부

## 문의

Issues 탭에서 문의해주세요.
