# Validation Rules & Scripts

## v6.4: Day of Week Validation (Claude Inference Bug)

### Problem
Claude 모델이 요일을 직접 추론할 때 하루씩 밀리는 버그가 있습니다.
예: 2026-01-11 (일요일) → Claude가 "토요일"로 잘못 추론

### Solution: Python datetime 강제 사용

```bash
# 정확한 요일 계산 (반드시 사용)
python3 -c "from datetime import datetime; d=datetime(YYYY,MM,DD); days=['월요일','화요일','수요일','목요일','금요일','토요일','일요일']; print(f'{d:%Y-%m-%d} ({days[d.weekday()]})')"
```

### fix_day_of_week.py

위치: `~/.pb-reports/fix_day_of_week.py`

```bash
# MCP raw 파일 수정
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json

# Validation 파일 수정
python3 ~/.pb-reports/fix_day_of_week.py ~/.pb-reports/validation-YYYY-MM-DD.json
```

기능:
- 파일명에서 날짜 추출 (YYYY-MM-DD)
- Python `datetime.weekday()`로 정확한 요일 계산
- 배열 형식 `[{...}]` MCP 파일 지원
- `pb_intel_report`, `portfolio_stage_briefing` 텍스트 내 요일 수정
- validation 파일의 `report_day`, `notion.title` 수정

### ❌ FORBIDDEN

| DO NOT | REASON |
|--------|--------|
| Claude가 직접 요일 추론 | 하루 밀림 버그 발생 |
| 수동 요일 계산 | 휴먼 에러 발생 가능 |
| fix_day_of_week.py 생략 | 잘못된 요일 저장 |

---

## v5.17: Template Enforcement (Pre-Slack)

### Main Message Validation

```python
def validate_main_message(message: str) -> tuple[bool, list[str]]:
    """Validate main Slack message before sending"""
    import re
    errors = []

    # Required elements
    required = [
        (":newspaper:", "Header emoji"),
        ("**PB 데일리 인텔리전스 브리핑", "Title"),
        ("━━━", "Separator line"),
        (":bar_chart:", "PB 성과 section"),
        (":rocket:", "Top Performers section"),
        (":rotating_light:", "Urgent section"),
        (":clipboard:", "Links section"),
        ("<!subteam^<YOUR_SLACK_SUBTEAM_ID>>", "Group tag"),
        ("🥇", "Medal 1"), ("🥈", "Medal 2"), ("🥉", "Medal 3"),
    ]

    for pattern, name in required:
        if pattern not in message:
            errors.append(f"Missing: {name}")

    # Count checks
    if message.count("**") // 2 < 10:
        errors.append("Bold count < 10")
    if message.count("•") < 5:
        errors.append("Bullet count < 5")

    # Forbidden patterns
    if re.search(r'_[^_\s]+_', message):
        errors.append("Italic detected")
    if "subteam<YOUR_SLACK_SUBTEAM_ID>" in message and "<!subteam" not in message:
        errors.append("Invalid group tag format")

    return len(errors) == 0, errors
```

### Brand Thread Validation

```python
def validate_brand_thread(thread: str, brand: str) -> tuple[bool, list[str]]:
    """Validate brand thread before sending"""
    errors = []

    if f"**{brand}**" not in thread:
        errors.append(f"Missing bold brand: **{brand}**")
    if ":fire:" not in thread and ":ice_cube:" not in thread:
        errors.append("Missing growth emoji")
    if thread.count("•") < 4:
        errors.append("Bullet count < 4 (v7.3: 어제/주간/노출/코호트)")
    if "백만" not in thread:
        errors.append("Missing GMV unit (백만)")

    return len(errors) == 0, errors
```

### Thread Count Check
ALL 9 brands required: 노어, 다나앤페타, 마치마라, 베르다, 브에트와, 아르앙, 지재, 퀸즈셀렉션, 희애

---

## v5.16: MCP Raw Integrity

### File Size Check
```bash
JSON_FILE=~/.pb-reports/mcp-raw-YYYY-MM-DD.json
FILE_SIZE=$(stat -f%z "$JSON_FILE" 2>/dev/null || stat -c%s "$JSON_FILE")
[[ $FILE_SIZE -lt 10000 ]] && echo "ERROR: File too small" && exit 1
```

### Structure Check
```bash
python3 ~/.pb-reports/validate_mcp_raw.py ~/.pb-reports/mcp-raw-YYYY-MM-DD.json
```

Checks: JSON valid, required keys exist, no placeholders, minimum length.

---

## v5.14: TOP 10 Products

### MCP vs Notion Comparison
```python
# Load MCP raw
mcp_products = pb_data["top_products"]  # from mcp-raw-YYYY-MM-DD.json

# Compare each product (1-10)
for i in range(10):
    mcp = mcp_products[i]
    notion = notion_products[i]

    # Check: rank, brand, name, GMV (±0.01), growth (±0.1%p)
    if mcp['brand'] != notion['brand']:
        errors.append(f"Rank {i+1} brand mismatch")
    if abs(mcp['gmv'] - notion['gmv']) > 0.01:
        errors.append(f"Rank {i+1} GMV mismatch")
```

---

## v5.13: JSON Storage Verification

### Pre-Step 3 Gate
```bash
JSON_FILE=~/.pb-reports/validation-YYYY-MM-DD.json

# Hard block if missing
[[ ! -f "$JSON_FILE" ]] && echo "ERROR: JSON not found" && exit 1
[[ ! -s "$JSON_FILE" ]] && echo "ERROR: JSON empty" && exit 1

# Validate structure
python3 -c "
import json, sys
with open('$JSON_FILE') as f:
    data = json.load(f)
    assert 'brands' in data and len(data['brands']) == 9
    assert 'top_products' in data and len(data['top_products']) == 10
    print('OK')
" || exit 1
```

---

## Numerical Validation (v5.12)

### Tolerance Rules
| Metric | Tolerance |
|--------|-----------|
| GMV (백만) | ±0.01 |
| SPV (원) | ±0.01 |
| Growth (%) | ±0.1%p |
| Sign (+/-) | Exact match |

### Sample Log Format
```
[Validation]
- 노어 GMV: 5.81백만 ✓
- 노어 성장률: +20.82% ✓
- Total PB GMV: 55.62백만 ✓
```

---

## Failure Behavior

```
IF validation fails:
  1. STOP immediately
  2. Log error details
  3. DO NOT send message
  4. Fix and re-validate

NEVER:
  - Skip validation
  - Ignore errors
  - Send without validation
```
