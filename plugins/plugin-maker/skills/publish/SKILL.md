---
name: publish
description: "Publish plugin to PB marketplace with automated clone, copy, register, and PR. Triggers: 'publish plugin', 'upload plugin', 'marketplace'"
---

# Marketplace Publisher

Guided PB marketplace publishing using `scripts/publish_to_pb.py`.

## Flow

### Step 1: Plugin Path

Ask: "Which plugin directory should I publish?"

Default to the current working directory. Verify the path contains `.claude-plugin/plugin.json`.

### Step 2: Dry Run

Ask: "Dry run first or publish directly?"

Options:
- **Dry run** (recommended for first time) - Preview all changes without modifying the marketplace repo
- **Publish** - Execute the full clone/copy/register/PR workflow

### Step 3: Version Bump

Ask: "Bump plugin version before publishing?"

Options:
- **None** - Keep current version
- **Patch** (e.g., 1.0.0 → 1.0.1) - Bug fixes
- **Minor** (e.g., 1.0.0 → 1.1.0) - New features
- **Major** (e.g., 1.0.0 → 2.0.0) - Breaking changes

### Step 4: Prerequisites Check

Before executing, verify these tools are installed:
- `gh` (GitHub CLI, authenticated)
- `git`
- `jq`
- `rsync`

Report any missing prerequisites and provide install instructions.

### Step 5: Marketplace Target

Ask: "Publish to default PB marketplace or a custom repo?"

Options:
- **Default** (`rapportlabs-pb-group/pb-plugins`) - Standard PB marketplace
- **Custom** - Ask for `owner/repo` format

### Step 6: Execute

Assemble and run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish_to_pb.py" <plugin-path> [--dry-run] [--version-bump patch|minor|major] [--repo owner/repo]
```

### Step 7: Results

- **Dry run**: Show what would be published. Ask if user wants to proceed with real publish.
- **Success**: Display the PR URL. Remind to review the PR before merging.
- **Failure**: Show error details. Common issues: secrets scan failure (run `/plugin-maker:check-secrets` first), missing `gh` auth, network errors.
