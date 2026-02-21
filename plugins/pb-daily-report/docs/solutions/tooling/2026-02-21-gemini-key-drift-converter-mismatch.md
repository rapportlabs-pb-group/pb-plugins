# Gemini Key Drift: Converter Key Mismatches

## Problem
2026-02-21 automated run produced Notion/Slack output with missing data:
- Brand snapshot section empty (9 brands missing)
- Growth rates showing N/A
- GMV/exposure shares missing
- Top 10 products missing brand/title columns
- MVP showing product-level instead of brand-level

## Root Cause
Gemini CLI output key names drifted from expected format in 4 ways:
1. `brand_snapshots` (plural) vs expected `brand_snapshot` (singular)
2. `gmv_wow_same_day_growth` (no `_percent` suffix) vs expected `gmv_wow_same_day_growth_percent`
3. `product` combined key `[브랜드] 상품명` vs expected separate `brand_name` + `display_title`
4. `gmv_share_y` (no `_percent` suffix) vs expected `gmv_share_y_percent`

## Solution
- `base.py`: Added `brand_snapshots` → `brand_snapshot` and `products_requiring_action` → `urgent_action_products` key mappings
- `sections.py`: Added fallback chains for growth rate keys (with/without `_percent` suffix)
- `sections.py`: Added regex parser for combined `[brand] product` format
- `sections.py`: Added brand-level MVP override from `brand_snapshot` growth data (v7.5 rule)
- Fixed in-place mutation bug by using shallow dict copy for MVP override

## Prevention
- Gemini output format is inherently variable. Always use fallback chains with multiple key variants.
- Pattern: `dict.get('specific_key', dict.get('general_key', default))`
- When adding new key normalization, update BOTH `base.py` (global normalization) AND section-specific fallbacks.
- Run converter on recent raw data after any key mapping change to verify output.

## Tags
gemini, key-drift, converter, fallback-chain, data-pipeline
