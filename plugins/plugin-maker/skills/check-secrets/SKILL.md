---
name: check-secrets
description: "Scan plugin for secrets, sensitive files, and hardcoded paths before distribution. Triggers: 'check secrets', 'scan secrets', 'security scan'"
---

# Secrets Scanner

Guided secrets scanning using `scripts/check_secrets.py`.

## Flow

### Step 1: Plugin Path

Ask: "Which plugin directory should I scan?"

Default to the current working directory (`.`). Accept absolute or relative paths.

### Step 2: Output Format

Ask: "Which output format?"

Options:
- **Human-readable** (default) - Formatted for terminal review
- **JSON** (`--json`) - Machine-readable for CI/CD pipelines

### Step 3: Strictness

Ask: "Strictness level?"

Options:
- **Normal** (default) - Fails only on errors (secrets found, missing .gitignore entries)
- **Strict** (`--strict`) - Also fails on warnings (potential issues that may be intentional)

### Step 4: Execute

Assemble and run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_secrets.py" [--json] [--strict] <plugin-path>
```

### Step 5: Results

- **Exit 0 (pass)**: Show success confirmation. Remind about pre-distribution checklist from root SKILL.md.
- **Exit 1 (fail)**: Show each finding with remediation guidance:
  - Sensitive files → add to `.gitignore` or remove
  - Hardcoded secrets → use environment variables or `${CLAUDE_PLUGIN_ROOT}`
  - Hardcoded user paths → replace with `${CLAUDE_PLUGIN_ROOT}` or `${CWD}`
  - Missing .gitignore entries → add recommended patterns

Offer to re-run after fixes with `/plugin-maker:check-secrets`.
