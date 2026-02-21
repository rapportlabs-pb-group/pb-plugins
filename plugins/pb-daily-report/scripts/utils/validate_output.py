#!/usr/bin/env python3
import json, sys, re

raw = sys.stdin.read().strip()
# CLI 래퍼 JSON
o = json.loads(raw)
if o.get("type") != "result" or o.get("is_error"):
    print("BAD: cli wrapper error"); sys.exit(2)

# error_max_turns 검증 - 턴 부족 시 실패 처리
if o.get("subtype") == "error_max_turns":
    print("BAD: hit max turns limit"); sys.exit(7)

# 모델 본문 단일라인 JSON 추출
m = re.search(r'\{.*\}', o.get("result",""))
if not m:
    print("BAD: missing inner json"); sys.exit(3)
inner = json.loads(m.group(0))

# 필수 필드 검증
need = ["status","notion_page_id","slack_ts","run_id"]
if not all(k in inner for k in need):
    print("BAD: missing fields"); sys.exit(4)
if inner["status"] != "ok":
    print("BAD: status not ok"); sys.exit(5)
if not inner["notion_page_id"] or not inner["slack_ts"]:
    print("BAD: empty ids"); sys.exit(6)

print("OK")