#!/usr/bin/env python3
import json, sys, subprocess, shlex, re

CLAUDE = "claude"

if len(sys.argv) != 2:
    print("usage: verify_artifacts.py RUN_ID", file=sys.stderr)
    sys.exit(2)
RUN_ID = sys.argv[1].strip()

wrapper = json.loads(sys.stdin.read().strip())
inner = json.loads(re.search(r'\{.*\}', wrapper.get("result","")).group(0))
page_id = inner["notion_page_id"]
slack_ts = inner["slack_ts"]

# 1) Notion 페이지에 RUN_ID 포함되어 있는지 (fetch)
prompt_notion = f"""
mcp__notionMCP__fetch 도구로 page_id={page_id} 내용을 가져와 RUN_ID={RUN_ID} 문자열이 내용/속성 어디든 포함되는지 확인해.
오직 'OK' 또는 'MISS' 한 단어만 출력해.
"""

r1 = subprocess.run([CLAUDE, "-p", prompt_notion, "--output-format", "json",
                     "--max-turns", "2", "--permission-mode", "bypassPermissions",
                     "--allowedTools", "mcp__notionMCP", "Read"],
                    capture_output=True, text=True, timeout=120)
if r1.returncode != 0:
    print("MISS: notion fetch failed"); sys.exit(3)
txt1 = r1.stdout
has_ok = re.search(r'"result"\s*:\s*"(OK|MISS)"', txt1)
if not has_ok or has_ok.group(1) != "OK":
    print("MISS: notion run_id not found"); sys.exit(4)

# 2) Slack 메시지 본문에 RUN_ID 포함되는지 (conversations.history)
prompt_slack = f"""
mcp__slack__conversations_history로 자동화 운영 채널의 최근 메시지를 조회해서, ts={slack_ts} 인 메시지를 찾아 RUN_ID={RUN_ID} 문자열이 본문에 포함되는지 확인해.
오직 'OK' 또는 'MISS' 한 단어만 출력해.
"""

r2 = subprocess.run([CLAUDE, "-p", prompt_slack, "--output-format", "json",
                     "--max-turns", "2", "--permission-mode", "bypassPermissions",
                     "--allowedTools", "mcp__slack", "Read"],
                    capture_output=True, text=True, timeout=120)
if r2.returncode != 0:
    print("MISS: slack fetch failed"); sys.exit(5)
txt2 = r2.stdout
has_ok2 = re.search(r'"result"\s*:\s*"(OK|MISS)"', txt2)
if not has_ok2 or has_ok2.group(1) != "OK":
    print("MISS: slack run_id not found"); sys.exit(6)

print("OK")