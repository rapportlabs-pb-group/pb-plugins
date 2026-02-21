# Top Performers Data Level Mismatch

## Problem
Slack Top Performers section displayed product-level growth rates (e.g., +189.7%)
alongside brand names, causing readers to misinterpret them as brand-level performance.
The same growth rates appeared in both Top Performers and Top 3 Products sections.

## Root Cause
Gemini CLI generates `top_performers` with product-level data (MVP/Rising Star are individual
products), but the Slack template used only the `brand_name` field without the product name.
This created a mapping mismatch:
- `top_performers[0].gmv_growth = "189.7%"` → product (셔츠 레이어드 니트 가디건)
- `brand_snapshot["다나앤페타"].yesterday_gmv = "+3.1%"` → actual brand growth

## Solution
Changed Slack template to use brand-level data for Top Performers:
- **Top Performers**: Use `brand_snapshot` for GMV growth (brand-level), cross-reference
  `top_10_growing_products` for the key product that drove growth
- **MVP header**: Use `brand_snapshot` growth rate for the top brand
- **주요 상품 TOP 3**: Keep product-level data (unchanged)

Template format changed from:
```
• *{브랜드} {±성장률}%* - {설명}
```
To:
```
• *{브랜드}* GMV {값}백만 (*{±브랜드_성장률}%*) - {대표_상품명}({±상품_성장률}%) 견인
```

## Prevention
- Always verify data source level (brand vs product) when displaying growth metrics
- Template now includes explicit data source rules table (v7.5)
- Validation checklist includes "Top Performers growth != product growth" check

## Tags
slack, template, data-level, brand-vs-product, top-performers, gemini
