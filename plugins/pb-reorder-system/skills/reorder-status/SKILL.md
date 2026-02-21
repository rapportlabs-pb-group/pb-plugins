---
name: reorder-status
description: "Use when checking reorder system status - shows brand versions, query/script status, and last update"
user_invocable: true
---

# /reorder-status

Check multi-brand reorder system status.

## Steps

1. Read CLAUDE.md Brands table for version info
2. List each brand's query and Apps Script versions
3. Read progress.md for last update date

## Output Format

| Brand | Query Ver | Script Ver | Status |
|-------|-----------|------------|--------|
| Noir | vX.X | vX.X | Production |
| Queens | vX.X | vX.X | Production |
| Verda | vX.X | vX.X | Production |
| Zizae | vX.X | vX.X | Production |
| Dana&Peta | vX.X | vX.X | Production |
| Marchmara | vX.X | vX.X | Production |

Last Updated: YYYY-MM-DD
