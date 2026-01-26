# 마켓플레이스 가이드

## 마켓플레이스 사용법

### 1. 마켓플레이스 추가

```bash
/plugin marketplace add rapportlabs-pb-group/pb-plugins
```

### 2. 플러그인 목록 확인

```bash
/plugin marketplace list
```

### 3. 플러그인 설치

```bash
/plugin install <plugin-name>@pb-plugins
```

### 4. 플러그인 업데이트

```bash
/plugin update <plugin-name>@pb-plugins
```

### 5. 플러그인 제거

```bash
/plugin uninstall <plugin-name>
```

## 플러그인 배포 절차

### 1. 새 플러그인 생성

```bash
# 저장소 클론
gh repo clone rapportlabs-pb-group/pb-plugins
cd pb-plugins

# 플러그인 생성
./scripts/create-plugin.sh my-plugin
```

### 2. 플러그인 개발

- `.claude-plugin/plugin.json` 수정
- `commands/` 에 명령어 추가
- `README.md` 작성

### 3. marketplace.json 업데이트

`.claude-plugin/marketplace.json`에 플러그인 등록:

```json
{
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./plugins/my-plugin",
      "description": "플러그인 설명",
      "version": "1.0.0",
      "author": { "name": "작성자" },
      "keywords": ["keyword"]
    }
  ]
}
```

### 4. PR 생성

```bash
git checkout -b add/my-plugin
git add .
git commit -m "Add my-plugin v1.0.0"
gh pr create --title "Add my-plugin" --body "새 플러그인 추가"
```

### 5. 리뷰 및 머지

- CI 검증 통과 확인
- 리뷰어 승인
- main 브랜치 머지 → 자동 배포

## 버전 업데이트

1. `plugin.json`의 `version` 수정
2. `marketplace.json`의 해당 플러그인 `version` 수정
3. CHANGELOG 업데이트
4. PR 생성
