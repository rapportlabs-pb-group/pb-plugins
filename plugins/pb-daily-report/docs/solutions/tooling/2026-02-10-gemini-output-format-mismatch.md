# Gemini CLI Output Format Mismatch in Converter

## Problem
`convert_mcp_to_notion.py` converter produced N/A values for all key metrics (GMV, SPV, weekly trend, brand snapshot, etc.) despite valid data in `mcp-raw-{date}.json`.

## Root Cause
Gemini CLI returns JSON with inconsistent key formats across runs:
1. **Case mismatch**: `GMV`/`SPV` (uppercase) vs expected `gmv`/`spv` (lowercase)
2. **Combined value strings**: `"30,132,922 (21.1% 🧊)"` instead of separate `gmv` + `gmv_growth` fields
3. **Korean key names**: `비중`, `노출_점유율` instead of English keys
4. **Varying structure keys**: `rows` vs `table_data` vs `brands`; `decline_in_performance` vs `performance_decline`; `segment_info` vs `category`
5. **Nested structure differences**: `channel_exposure_share_yesterday` vs `channel_exposure_yesterday`

## Solution
Defensive key lookups with fallback chains + combined format parsing:
```python
# Always check multiple key variants
raw = d.get('gmv_y', d.get('GMV', 'N/A'))
# Parse combined "value (growth%)" format
m = re.match(r'^([0-9,.]+)\s*\((.+)\)$', raw.strip())
```

Total 9 fixes applied to `~/.pb-reports/converters/sections.py` + 1 to `base.py`.

## Prevention
- Always add uppercase + Korean key variants in `.get()` fallback chains
- Add `products_needing_action` type key mappings in `base.py` immediately
- When Gemini prompt changes, run converter on sample output and verify all sections before deploy
- Consider adding a "key normalization" pass in `parse_pb_intel_report()` that lowercases all keys

## Tags
gemini, converter, json-parsing, key-mismatch, notion, pb-daily-report
