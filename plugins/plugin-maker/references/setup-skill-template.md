# Setup Skill Template

Reference for generating `:setup` skills inside plugins. Based on omc-setup patterns.

## When to Use

When `init_plugin.py` generates a new plugin (default behavior unless `--no-setup`), it creates `skills/setup/SKILL.md` inside the plugin using this template.

## State Management

State file: `.plugin-state/setup-state.json`

```json
{
  "lastCompletedStep": 2,
  "timestamp": "2025-01-15T10:30:00+09:00",
  "pluginName": "my-plugin"
}
```

### Resume Detection

```bash
STATE_FILE=".plugin-state/setup-state.json"

if [ -f "$STATE_FILE" ]; then
  TIMESTAMP_RAW=$(jq -r '.timestamp // empty' "$STATE_FILE" 2>/dev/null)
  NOW_EPOCH=$(date +%s)

  # Cross-platform epoch conversion
  if TIMESTAMP_EPOCH=$(date -d "$TIMESTAMP_RAW" +%s 2>/dev/null); then
    :
  else
    CLEAN=$(echo "$TIMESTAMP_RAW" | sed 's/[+-][0-9][0-9]:[0-9][0-9]$//' | sed 's/T/ /')
    TIMESTAMP_EPOCH=$(date -j -f "%Y-%m-%d %H:%M:%S" "$CLEAN" +%s 2>/dev/null || echo 0)
  fi

  STATE_AGE=$((NOW_EPOCH - TIMESTAMP_EPOCH))
  if [ "$STATE_AGE" -gt 86400 ]; then
    echo "Previous state is stale (>24h). Starting fresh."
    rm -f "$STATE_FILE"
  else
    LAST_STEP=$(jq -r '.lastCompletedStep // 0' "$STATE_FILE")
    echo "Found previous session at step $LAST_STEP"
  fi
fi
```

### Save Progress Helper

```bash
save_progress() {
  mkdir -p .plugin-state
  cat > ".plugin-state/setup-state.json" << EOF
{
  "lastCompletedStep": $1,
  "timestamp": "$(date '+%Y-%m-%dT%H:%M:%S%z')",
  "pluginName": "${PLUGIN_NAME}"
}
EOF
}
```

### Clear on Completion

```bash
rm -f ".plugin-state/setup-state.json"
echo "Setup complete. State cleared."
```

## Idempotent Operations Pattern

All setup steps must be safe to re-run:

```bash
# Directory creation
mkdir -p ./config

# File creation (only if missing)
[ -f ./config/settings.json ] || echo '{}' > ./config/settings.json

# Dependency install (idempotent by nature)
pip install -q -r requirements.txt 2>/dev/null || true
npm install --silent 2>/dev/null || true
```

## Generated SKILL.md Template

This is the template that `init_plugin.py` generates at `skills/setup/SKILL.md`:

```markdown
---
name: setup
description: "Initial setup for PLUGIN_NAME. Run after installing the plugin."
---

# PLUGIN_NAME Setup

## Step 0: Resume Detection

Check for existing setup state:

\`\`\`bash
STATE_FILE=".plugin-state/setup-state.json"
if [ -f "$STATE_FILE" ]; then
  LAST_STEP=$(jq -r '.lastCompletedStep // 0' "$STATE_FILE" 2>/dev/null)
  echo "Found previous session at step $LAST_STEP"
fi
\`\`\`

If state exists, ask user: "Resume from step $LAST_STEP or start fresh?"

## Step 1: Check Environment

Verify required tools are available:

\`\`\`bash
# TODO: Add your prerequisites here
command -v python3 >/dev/null 2>&1 || { echo "python3 required"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "git required"; exit 1; }
echo "Environment OK"
\`\`\`

Save progress after completion.

## Step 2: Install Dependencies

\`\`\`bash
# TODO: Add your dependency installation here
# pip install -q -r "${CLAUDE_PLUGIN_ROOT}/requirements.txt" 2>/dev/null || true
# npm install --silent 2>/dev/null || true
echo "Dependencies installed"
\`\`\`

Save progress after completion.

## Step 3: Configure

\`\`\`bash
# TODO: Add your configuration steps here
mkdir -p .plugin-state
echo "Configuration complete"
\`\`\`

Save progress after completion.

## Step 4: Validate

\`\`\`bash
# TODO: Add validation checks here
echo "Validation passed"
\`\`\`

Clear state file on success:
\`\`\`bash
rm -f ".plugin-state/setup-state.json"
echo "Setup complete!"
\`\`\`
```

## Plugin Creator Instructions

When generating the setup skill, replace:
- `PLUGIN_NAME` with the actual plugin name
- `TODO` markers indicate sections the plugin creator should customize
- Add `.plugin-state/` to the plugin's `.gitignore`
