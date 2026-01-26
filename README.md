# PB Plugins Marketplace

라포랩스 Pb 그룹의 Claude Code 플러그인 마켓플레이스입니다.

## Quick Start

```bash
# 마켓플레이스 추가
/plugin marketplace add rapportlabs-pb-group/pb-plugins

# 플러그인 설치
/plugin install <plugin-name>@pb-plugins

# 플러그인 사용
/<plugin-name>:<command>
```

## 플러그인 목록

| 플러그인 | 설명 | 버전 |
|---------|------|-----|
| example-plugin | 예제 플러그인 - 새 플러그인 참고용 | 1.0.0 |

## 플러그인 개발

### 빠른 시작

```bash
# 저장소 클론
gh repo clone rapportlabs-pb-group/pb-plugins
cd pb-plugins

# 새 플러그인 생성
./scripts/create-plugin.sh my-plugin

# marketplace.json에 등록 후 PR 생성
```

### 필수 구조

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json       # 필수
├── commands/             # 필수
│   └── main.md
└── README.md             # 필수
```

## 문서

- [플러그인 개발 가이드](docs/PLUGIN_GUIDE.md)
- [마켓플레이스 가이드](docs/MARKETPLACE_GUIDE.md)
- [기여 가이드](CONTRIBUTING.md)

## 문의

[Issues](https://github.com/rapportlabs-pb-group/pb-plugins/issues) 탭에서 문의해주세요.
