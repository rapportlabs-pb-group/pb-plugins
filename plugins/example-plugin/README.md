# Example Plugin

PB 플러그인 마켓플레이스 예제 플러그인입니다.

## 설치

```bash
/plugin install example-plugin@pb-plugins
```

## 사용

```bash
/example-plugin:hello
```

## 구조

```
example-plugin/
├── .claude-plugin/
│   └── plugin.json       # 플러그인 메타데이터
├── commands/
│   └── hello.md          # 인사 명령어
└── README.md
```

## 새 플러그인 만들기

이 구조를 참고하여 자신만의 플러그인을 만들어보세요!
