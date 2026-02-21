---
name: reorder-deploy
description: "Use when deploying Apps Script to all brands - runs clasp pull then push for each brand"
user_invocable: true
---

# /reorder-deploy

Deploy Apps Script to all 6 brands.

## Steps

1. Run `clasp pull` for all brands (sync cloud changes first)
2. Confirm local changes with user
3. Run `clasp push` for all brands

## Command

```bash
for d in noir queens verda zizae danapeta marchmara; do
  echo "=== $d ===" && (cd apps_scripts/$d && clasp pull && clasp push)
done
```

## Rules
- Always pull before push (preserve other people's cloud changes)
- Ask user for confirmation if conflicts detected
